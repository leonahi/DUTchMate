#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "usb_connection.c"

static struct dmh_uart_rx_ring ring;
static uint64_t now_us, completed_at, completion_sequence;
static bool adc_active, adc_done, config_ready, config_enabled, response_ready;
static bool dtr = true;
static bool fail_tx;
static unsigned irq_depth;
static bool race_mode, inject_completion;
static void complete(uint64_t at);
static void uart(uint64_t at);

unsigned int irq_lock(void) {
 if (inject_completion && irq_depth==0) {
  inject_completion=false; race_mode=false;
  complete(100); uart(110); now_us=120;
 }
 return irq_depth++;
}
void irq_unlock(unsigned int key) { irq_depth = key; }
uint64_t time_us_64(void) { return now_us; }
void k_sleep(int ticks) { (void)ticks; }
int uart_line_ctrl_get(const struct device *dev, int field, uint32_t *value)
{ (void)dev; (void)field; *value = dtr; return 0; }
int uart_line_ctrl_set(const struct device *dev, int field, uint32_t value)
{ (void)dev; (void)field; (void)value; return 0; }
bool device_is_ready(const struct device *dev) { (void)dev; return true; }
int dutchmate_cdc_tx_initialize(const struct device *dev) { (void)dev; return 0; }
enum dmh_cdc_tx_result dutchmate_cdc_tx_start(const uint8_t *frame, size_t length)
{ if (!fail_tx && dtr) fwrite(frame,1,length,stdout); return DMH_CDC_TX_PENDING; }
enum dmh_cdc_tx_result dutchmate_cdc_tx_poll(void)
{ return fail_tx ? DMH_CDC_TX_INVALID_ARGUMENT : DMH_CDC_TX_COMPLETED; }
void dutchmate_cdc_tx_cancel(void) {}
int dutchmate_command_runtime_initialize(const struct device *dev) { (void)dev; return 0; }
bool dutchmate_command_runtime_on_cdc_rx_ready(const struct device *dev) { (void)dev; return false; }
void dutchmate_command_runtime_discard_input(void) {}
int dutchmate_command_runtime_start_epoch(void) { return 0; }
int dutchmate_command_runtime_end_epoch(void) { config_ready=false; return 0; }
bool dutchmate_command_runtime_faulted(void) { return false; }
bool dutchmate_command_runtime_take_response(const char **response,size_t *length)
{ if (!response_ready) return false; response_ready=false;
  *response="{\"ok\":true,\"timestamp_us\":0}\n"; *length=strlen(*response); return true; }
void dutchmate_command_runtime_response_sent(void) { config_ready=true; }
bool dutchmate_command_runtime_take_sense_configuration(bool *enabled)
{ if (!config_ready) return false; config_ready=false; *enabled=config_enabled; return true; }
int dutchmate_uart_rx_start(void) { return 0; }
void dutchmate_uart_rx_stop(void) {}
bool dutchmate_uart_rx_faulted(void) { return false; }
void dutchmate_uart_rx_snapshot_observation(struct dmh_uart_rx_snapshot *snapshot,uint64_t *seq)
{ dmh_uart_rx_ring_snapshot_observation(&ring,snapshot,seq); }
int dutchmate_uart_rx_take_before(bool limit,uint64_t seq,uint8_t *out,size_t capacity,
 enum dmh_uart_rx_observation_kind *kind,struct dmh_uart_rx_chunk *chunk,struct dmh_uart_rx_overflow *overflow)
{ assert(irq_depth>0); return dmh_uart_rx_ring_take_before(&ring,limit,seq,out,capacity,kind,chunk,overflow); }
int dutchmate_platform_io_force_safe(void) { return 0; }
static int adc_start(void *context) { (void)context; adc_active=true; adc_done=false; return 0; }
static enum dmh_vio_adc_result adc_poll(void *context,uint16_t *raw,uint64_t *done,uint64_t *sequence)
{ (void)context; if (!adc_done) { if (race_mode) inject_completion=true; return DMH_VIO_ADC_PENDING; }
  adc_active=false; adc_done=false; *raw=2048; *done=completed_at; *sequence=completion_sequence; return DMH_VIO_ADC_COMPLETE; }
struct dmh_vio_adc_port dutchmate_platform_vio_port(void)
{ return (struct dmh_vio_adc_port){.start=adc_start,.poll=adc_poll}; }
bool dutchmate_platform_vio_completion_ready(void) { return adc_active && adc_done; }
static void complete(uint64_t at)
{ struct dmh_uart_rx_snapshot snapshot; completed_at=at; adc_done=true;
  dutchmate_uart_rx_snapshot_observation(&snapshot,&completion_sequence); }
static void uart(uint64_t at)
{ const uint8_t data='X'; assert(dmh_uart_rx_ring_push(&ring,0,at,&data,1)==0); }
int main(int argc,char **argv)
{
 assert(argc==2); struct dmh_telemetry_schedule schedule;
 struct dmh_vio_adc_port port=dutchmate_platform_vio_port();
 dmh_uart_rx_ring_init(&ring); dmh_telemetry_schedule_init(&schedule);
 dmh_vio_sense_init(&vio_sense,&port,3300,false);
 response_ready=true; config_enabled=true;
 if (!strcmp(argv[1],"failed-ack")) fail_tx=true;
 if (!strcmp(argv[1],"interrupted-ack")) dtr=false;
 int result=drain_one_output(&schedule);
 if (fail_tx || !dtr) { assert(result<0); assert(!vio_sense.enabled && !adc_active); return 0; }
 assert(result==1 && vio_sense.enabled && adc_active);
 uart(50);
 if (!strcmp(argv[1],"completion-race")) { now_us=90; race_mode=true; }
 else { complete(100); uart(110); now_us=120; stage_vio(); }
 if (!strcmp(argv[1],"disable-pending")) {
  response_ready=true; config_enabled=false;
  assert(drain_one_output(&schedule)==1); assert(!vio_pending && !vio_sense.enabled);
 }
 while (drain_one_output(&schedule)>0) {}
 return 0;
}
