import time
import statistics

import assistant


def run_once(cmd: str) -> float:
    t0 = time.perf_counter()
    _ = assistant.run_feature(cmd)
    return time.perf_counter() - t0


def main():
    assistant.initialize_assistant()
    tests = [
        "mấy giờ rồi",
        "mở notepad",
        "thời tiết ở hà nội",
        "tính 25 chia 5",
        "xem thông tin hệ thống",
        "ai là albert einstein?",
    ]

    # warmup
    for t in tests:
        _ = assistant.run_feature(t)

    print("Performance (seconds):")
    for t in tests:
        samples = [run_once(t) for _ in range(3)]
        print(f"- {t}: min={min(samples):.3f} avg={statistics.mean(samples):.3f} max={max(samples):.3f}")


if __name__ == "__main__":
    main()

