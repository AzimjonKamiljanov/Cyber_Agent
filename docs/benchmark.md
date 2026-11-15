# Uzbek Voice & Command Benchmark Results

**Date:** 2026-11-15 18:26:10  
**Mode:** `text-dry-run`  
**Dataset:** `tests/benchmark/uzbek_100.jsonl` (tested: 100 items)  

## Summary Metrics
| Metric | Value | Target | Status |
|---|---|---|---|
| **Intent Accuracy** | **96.0%** (96/100) | ≥ 90% | PASS |
| **Tier Policy Accuracy** | **100.0%** (100/100) | 100% | PASS |
| **Execution Latency** | **0.00 ms / query** | < 50 ms | PASS |
| **TTS MOS Score** | USER-RATED | ≥ 4.0 | USER-TEST-REQUIRED |

## Sample Evaluation Table (First 15 items)
| ID | Category | Text (UZ) | Expected Intent | Predicted Intent | Tier | Match |
|---|---|---|---|---|---|---|
| cmd_01 | simple_commands | Hozir soat necha bo'ldi? | `get_local_time` | `get_local_time` | GREEN | ✅ |
| cmd_02 | simple_commands | Toshkentda hozirgi vaqtni aytib ber | `get_local_time` | `get_local_time` | GREEN | ✅ |
| cmd_03 | simple_commands | Tizim holatini ko'rsat | `get_system_status` | `get_system_status` | GREEN | ✅ |
| cmd_04 | simple_commands | Noutbukda qancha RAM bo'sh qoldi? | `get_system_status` | `get_system_status` | GREEN | ✅ |
| cmd_05 | simple_commands | GPU harorati va yuklanishi qanday? | `get_system_status` | `get_system_status` | GREEN | ✅ |
| cmd_06 | simple_commands | Batareya quvvati necha foiz? | `get_system_status` | `get_system_status` | GREEN | ✅ |
| cmd_07 | simple_commands | Ovoz balandligini 50 ga qo'y | `set_volume` | `set_volume` | GREEN | ✅ |
| cmd_08 | simple_commands | Ovozni 80 foizga ko'tar | `set_volume` | `set_volume` | GREEN | ✅ |
| cmd_09 | simple_commands | Ovozni 0 ga tushir, o'chir | `set_volume` | `set_volume` | GREEN | ✅ |
| cmd_10 | simple_commands | Mavjud taymerlarni ko'rsat | `list_timers` | `list_timers` | GREEN | ✅ |
| cmd_11 | simple_commands | Qanday taymerlarim bor? | `list_timers` | `list_timers` | GREEN | ✅ |
| cmd_12 | simple_commands | Terminal ilovasini och | `open_allowed_app` | `open_allowed_app` | GREEN | ✅ |
| cmd_13 | simple_commands | Brauzerni ishga tushir | `open_allowed_app` | `open_allowed_app` | GREEN | ✅ |
| cmd_14 | simple_commands | Kalkulyatorni och | `open_allowed_app` | `open_allowed_app` | GREEN | ✅ |
| cmd_15 | simple_commands | Matn muharririni och | `open_allowed_app` | `open_allowed_app` | GREEN | ✅ |
