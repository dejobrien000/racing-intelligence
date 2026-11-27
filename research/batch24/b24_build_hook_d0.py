"""Batch 23 C8 research: hook frame with a different starting level for horses without a held run (debut_offset_kg), all else as frozen."""
import os
import engine.lab as L
L.PN_FROZEN = dict(L.PN_FROZEN, debut_offset_kg=float(os.environ['D0'])); print('debut_offset_kg', L.PN_FROZEN['debut_offset_kg'])
U = L.build(os.environ['LAB_OUT']); print(len(U), 'rows; d0 frame written')
