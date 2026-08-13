"""Shared CLI validation and structured input helpers."""

import argparse
import math
import os


MESSAGE_ENV = "XIAOAI_TTS_MESSAGE"
SCOPE_ENV = "XIAOAI_TTS_SCOPE"


def max_chars_value(raw_value):
    value = int(raw_value)
    if value <= 0:
        raise argparse.ArgumentTypeError("--max-chars must be greater than 0")
    return value


def positive_timeout_value(raw_value):
    value = int(raw_value)
    if value <= 0:
        raise argparse.ArgumentTypeError("--timeout must be greater than 0")
    return value


def nonnegative_pause_value(raw_value):
    value = float(raw_value)
    if not math.isfinite(value) or value < 0:
        raise argparse.ArgumentTypeError("--pause must be 0 or greater")
    return value


def speed_value(raw_value):
    value = float(raw_value)
    if not 0.8 <= value <= 2.0:
        raise argparse.ArgumentTypeError("--speed must be between 0.8 and 2.0")
    return value


def default_scope(fallback):
    return os.environ.get(SCOPE_ENV) or fallback


def read_message_from_env():
    if MESSAGE_ENV not in os.environ:
        raise ValueError(f"--from-env requires {MESSAGE_ENV} to be set")
    return os.environ[MESSAGE_ENV]
