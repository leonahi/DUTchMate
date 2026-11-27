#include "platform_io.h"
#include "sense_pin_probe_stubs.h"

#include <stdio.h>
#include <string.h>

struct device test_gpio0 = { .ready = true };
struct test_pad_registers test_pads;
static unsigned int modes[30];
static int levels[30];
static bool fail_sense_configuration;

#ifdef CONFIG_DUTCHMATE_SENSE_PAD_REPORT
static int check_pad_report(bool bounds)
{
	char output[22];
	int result;

	/* Distinguish the selected pad and require a fresh read on each call. */
	test_pads.io[27] = 0xDEADBEEFU;
	test_pads.io[28] = 0x192U;
	memset(output, '#', sizeof(output));
	result = dutchmate_platform_sense_probe_firmware(output, 21U);
	if (result != 0 || strcmp(output, "sensepad-2-p00000192") != 0 ||
	    output[21] != '#') {
		fprintf(stderr, "live pad report missing or incorrect: result=%d\n", result);
		return 1;
	}
	if (bounds) {
		if (dutchmate_platform_sense_probe_firmware(output, 20U) != -ENOSPC ||
		    dutchmate_platform_sense_probe_firmware(output, 0U) != -ENOSPC ||
		    dutchmate_platform_sense_probe_firmware(NULL, 21U) != -EINVAL ||
		    output[21] != '#') {
			fprintf(stderr, "pad report did not enforce output capacity\n");
			return 1;
		}
	} else {
		test_pads.io[28] = 0x116U;
		result = dutchmate_platform_sense_probe_firmware(output, sizeof(output));
		if (result != 0 || strcmp(output, "sensepad-2-p00000116") != 0 ||
		    test_pads.io[27] != 0xDEADBEEFU || test_pads.io[28] != 0x116U) {
			fprintf(stderr, "pad report was stale or changed pad registers\n");
			return 1;
		}
	}
	return 0;
}
#endif

int gpio_pin_configure(const struct device *port, unsigned int pin, unsigned int flags)
{
	if (port != &test_gpio0 || pin >= 30U) {
		return -EINVAL;
	}
	if (pin == 28U && fail_sense_configuration) {
		return -EIO;
	}
	modes[pin] = flags;
	return 0;
}

int gpio_pin_set(const struct device *port, unsigned int pin, int value)
{
	if (port != &test_gpio0 || pin >= 30U) {
		return -EINVAL;
	}
	levels[pin] = value;
	return 0;
}

int main(int argc, char **argv)
{
	const unsigned int outputs[] = { 2U, 11U, 8U, 7U, 26U, 22U, 9U, 10U, 20U, 21U };
	const unsigned int inputs[] = { 15U, 14U, 13U, 12U };
	int result;

	if (argc != 2) {
		return 2;
	}
#ifdef CONFIG_DUTCHMATE_SENSE_PAD_REPORT
	if (strcmp(argv[1], "pad-report") == 0) {
		return check_pad_report(false);
	}
	if (strcmp(argv[1], "pad-report-bounds") == 0) {
		return check_pad_report(true);
	}
#endif
	for (unsigned int pin = 0U; pin < 30U; pin++) {
		modes[pin] = 0xFFFFU;
		levels[pin] = -1;
	}
	/* Hardware boundary fixture: disconnected controls before releasing ISO. */
	test_pads.io[27] = 0x123U;
	test_pads.io[28] = 0x192U;
	fail_sense_configuration = strcmp(argv[1], "configure-error") == 0;
	result = dutchmate_platform_io_initialize_safe();
	if (fail_sense_configuration) {
		if (result != -EIO) {
			fprintf(stderr, "sense configuration error was not propagated: %d\n", result);
			return 1;
		}
		if (test_pads.io[28] != 0x192U) {
			fprintf(stderr, "ISO changed after a failed GPIO configuration\n");
			return 1;
		}
		return 0;
	}
	if (result != 0) {
		fprintf(stderr, "initialization failed: %d\n", result);
		return 1;
	}
	if (modes[28] != GPIO_DISCONNECTED) {
		fprintf(stderr, "unexpected GP28 configuration: %u\n", modes[28]);
		return 1;
	}
	if (levels[28] != -1) {
		fprintf(stderr, "sense pin was driven\n");
		return 1;
	}
	if (test_pads.io[28] != 0x92U || test_pads.io[27] != 0x123U) {
		fprintf(stderr, "ISO release did not clear only GP28 ISO: %x\n", test_pads.io[28]);
		return 1;
	}
	for (size_t index = 0U; index < ARRAY_SIZE(outputs); index++) {
		unsigned int pin = outputs[index];

		if (modes[pin] != GPIO_OUTPUT_INACTIVE || levels[pin] != 0) {
			fprintf(stderr, "unsafe output state on GPIO%u\n", pin);
			return 1;
		}
	}
	for (size_t index = 0U; index < ARRAY_SIZE(inputs); index++) {
		if (modes[inputs[index]] != GPIO_INPUT) {
			fprintf(stderr, "event input configuration changed\n");
			return 1;
		}
	}
	return 0;
}
