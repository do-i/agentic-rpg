# Profiling

Rule: do not optimize render/update code until a profile identifies a hotspot.

## Quick start

```sh
python -m engine.main --scenario ./rusted_kingdoms --profile profile.prof
```

Play the part you care about (walk the world map, open menus, fight a
battle), then quit. On exit the top 30 functions by cumulative time are
printed and the raw pstats data lands in `profile.prof`. The dump also
happens on Ctrl-C, so an interrupted session still yields a profile.

## Reproducible profiles via playback

The default `--mode record` writes every input to `recording.pkl`. Replay
the same session under the profiler to compare before/after numbers on
identical input:

```sh
# 1. play once to produce recording.pkl (recorded by default)
python -m engine.main --scenario ./rusted_kingdoms

# 2. profile the exact same session, faster than realtime if desired
python -m engine.main --scenario ./rusted_kingdoms \
    --mode playback --playback-speed 4 --profile profile.prof
```

## Reading the results

```sh
python -m pstats profile.prof   # interactive: sort cumtime / stats 20
```

or `pip install snakeviz && snakeviz profile.prof` for a flame-graph view.

Frame cost lives under `Game.run`: `SceneManager.update` is game logic,
`SceneManager.render` is drawing, `present_frame`/`pygame.display.flip`
is scaling plus vsync. Time inside `flip` is usually the display waiting
for vsync, not real work — look at `update`/`render` children first.
