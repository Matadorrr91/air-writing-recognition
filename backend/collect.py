"""Gelabeltes Sammeln von Trainingssegmenten.

Startet einen WebSocket-Server, mit dem sich die Watch-App verbindet. Das
Terminal zeigt fortlaufend, welche Ziffer als naechstes zu schreiben ist.
Sobald die Segmentierung eine Schreibung erkennt (Ziffer + Pause), wird sie
unter dem aktuellen Ziel-Label gespeichert und die naechste Ziffer angezeigt.

Aufruf:
    python -m backend.collect --person max
    python -m backend.collect --person lisa --count 80 --shuffle

Hinweise:
    - Vor dem Start die Watch-App auf diese Laptop-IP + Port zeigen lassen.
    - Pro erkanntem Segment wird automatisch zur naechsten Ziffer gewechselt.
    - Fehlerhafte Aufnahmen koennen als Datei aus dataset/ geloescht werden.
"""

import argparse
import asyncio
import json

import numpy as np
import websockets

from . import config, data
from .segmentation import Segmenter


def build_schedule(digits: list[int], count: int, shuffle: bool, seed: int) -> list[int]:
    schedule = [d for _ in range(count) for d in digits]
    if shuffle:
        rng = np.random.default_rng(seed)
        rng.shuffle(schedule)
    return schedule


class Collector:
    def __init__(self, person: str, schedule: list[int]):
        self.person = person
        self.schedule = schedule
        self.ptr = 0

    def _prompt(self):
        if self.ptr >= len(self.schedule):
            print("\n*** Fertig! Alle Segmente gesammelt. Strg+C zum Beenden. ***")
            return
        target = self.schedule[self.ptr]
        print(f"\n>>> Schreibe jetzt:  [ {target} ]   ({self.ptr + 1}/{len(self.schedule)})")

    async def handle(self, ws):
        print(f"Watch verbunden ({self.person}).")
        self._prompt()
        seg = Segmenter()
        async for message in ws:
            try:
                sample = json.loads(message)
            except json.JSONDecodeError:
                continue
            result = seg.push(sample)
            if result is None or self.ptr >= len(self.schedule):
                continue
            label = self.schedule[self.ptr]
            idx = data.next_index(label, self.person)
            data.save_segment(result, label, self.person, idx)
            print(f"    gespeichert: Ziffer {label}, {len(result)} Samples")
            self.ptr += 1
            self._prompt()


async def run(args):
    digits = [int(c) for c in args.digits]
    schedule = build_schedule(digits, args.count, args.shuffle, args.seed)
    collector = Collector(args.person, schedule)
    print(f"Sammel-Server auf ws://{config.HOST}:{config.PORT}  (Person: {args.person})")
    print(f"Plan: {args.count}x je Ziffer {digits}  =>  {len(schedule)} Segmente")
    async with websockets.serve(collector.handle, config.HOST, config.PORT, max_size=None):
        await asyncio.Future()   # laeuft bis Strg+C


def main():
    p = argparse.ArgumentParser(description="Gelabelte Air-Writing-Segmente sammeln.")
    p.add_argument("--person", required=True, help="ID der schreibenden Person (z.B. max)")
    p.add_argument("--count", type=int, default=60, help="Aufnahmen pro Ziffer")
    p.add_argument("--digits", type=str, default="0123456789", help="Welche Ziffern sammeln")
    p.add_argument("--shuffle", action="store_true", help="Reihenfolge mischen")
    p.add_argument("--seed", type=int, default=0)
    args = p.parse_args()
    try:
        asyncio.run(run(args))
    except KeyboardInterrupt:
        print("\nBeendet.")


if __name__ == "__main__":
    main()
