# Phase 3 Moving results

All 16 Moving cases passed in Vivado/XSim 2025.1.1, including
5 intended invalid-configuration rejections.
Positive units verify 256 patterns; integrations verify 1024 complete patterns
at lengths 64,128,200 with four phase-distinct chains and independent feedback.

- [Case statuses and actual durations](reports/moving_verification_summary.csv)
- [Dedicated integration measurements](reports/moving_wtm_summary.csv)
- [Complete Phase 3 report and reproduction](../Comparison/README.md)
- [Architecture and physical scan ordering](../../../docs/moving_control.md)
- [Focused captured boundary](waveforms/moving_beta16_first_switch.svg)
- [Source, active modes and scan-feedback trace](waveforms/moving_beta16_integration.svg)

Full WDB histories and portable VCDs exist locally under waveforms and are
Git-ignored generated files. WCFG layouts reference the adjacent WDB by basename.
No processor-level fault coverage or physical power result is claimed.
