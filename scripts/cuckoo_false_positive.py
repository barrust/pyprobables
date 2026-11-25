"""Measure cuckoo filter false positives using reproducible, disjoint key sets."""

import argparse
import random
import statistics
import sys
import time

from probables import CountingCuckooFilter, CuckooFilter


def positive_int(value: str) -> int:
    result = int(value)
    if result <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return result


def error_rate(value: str) -> float:
    result = float(value)
    if not 0 < result < 1:
        raise argparse.ArgumentTypeError("must be between zero and one")
    return result


def make_keys(seed: int, count: int, prefix: str):
    rng = random.Random(seed)
    for _ in range(count):
        yield f"{prefix}-{rng.getrandbits(128):032x}"


def run_iteration(filter_class, args, iteration: int) -> tuple[int, int]:
    seed = args.seed + iteration
    random.seed(seed)
    start = time.perf_counter()
    cko = filter_class.init_error_rate(
        args.error_rate,
        capacity=args.capacity,
        bucket_size=args.bucket_size,
        auto_expand=not args.no_auto_expand,
    )
    for key in make_keys(seed, args.keys, "key"):
        cko.add(key)
    missing = sum(not bool(cko.check(key)) for key in make_keys(seed, args.keys, "key"))
    hits = sum(bool(cko.check(key)) for key in make_keys(seed + args.iterations, args.queries, "query"))
    allocated_buffers = sum(
        sys.getsizeof(buffer)
        for layer in cko._layers
        for buffer in (layer.fingerprints, layer.occupied, layer.counts)
        if buffer is not None
    )
    print(
        f"{filter_class.__name__} run={iteration + 1} seed={seed} "
        f"inserted={cko.elements_added}/{args.keys} "
        f"capacity={cko.capacity} slots={cko.capacity * cko.bucket_size} "
        f"load={cko.load_factor():.6f} fingerprint_bits={cko.fingerprint_size_bits} "
        f"layers={len(cko._layers)} allocated_buffer_bytes={allocated_buffers} "
        f"false_negatives={missing} false_positives={hits}/{args.queries} "
        f"rate={hits / args.queries:.8g} elapsed={time.perf_counter() - start:.2f}s",
        flush=True,
    )
    return hits, missing


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--error-rate", type=error_rate, default=0.001, help="target rate (default: 0.001)")
    parser.add_argument("--keys", type=positive_int, default=100_000, help="insertions per run (default: 100000)")
    parser.add_argument("--queries", type=positive_int, default=1_000_000, help="queries per run (default: 1000000)")
    parser.add_argument("--iterations", type=positive_int, default=5, help="independent runs (default: 5)")
    parser.add_argument("--capacity", type=positive_int, default=30_000, help="initial bucket count (default: 30000)")
    parser.add_argument("--bucket-size", type=positive_int, default=4, help="slots per bucket (default: 4)")
    parser.add_argument("--seed", type=int, default=20000, help="initial random seed (default: 20000)")
    parser.add_argument("--filter", choices=("cuckoo", "counting", "both"), default="both", help="filter to measure")
    parser.add_argument("--no-auto-expand", action="store_true", help="fail if the initial table cannot hold the keys")
    args = parser.parse_args()

    classes = {
        "cuckoo": (CuckooFilter,),
        "counting": (CountingCuckooFilter,),
        "both": (CuckooFilter, CountingCuckooFilter),
    }
    print(f"target_error_rate={args.error_rate} iterations={args.iterations}", flush=True)
    missing_total = 0
    for filter_class in classes[args.filter]:
        results = [run_iteration(filter_class, args, i) for i in range(args.iterations)]
        rates = [hits / args.queries for hits, _ in results]
        missing_total += sum(missing for _, missing in results)
        print(
            f"{filter_class.__name__} summary: mean_rate={statistics.mean(rates):.8g} "
            f"min_rate={min(rates):.8g} max_rate={max(rates):.8g} "
            f"total_false_positives={sum(hits for hits, _ in results)}/{args.queries * args.iterations}",
            flush=True,
        )
    if missing_total:
        print(f"ERROR: {missing_total} inserted keys checked as absent", flush=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
