import datetime

one_day = datetime.timedelta(1)
twelve_hours = datetime.timedelta(0, 43200)

format_value_range = {'12h': 4320000, '24h': 8640000}


def get_format(chip_nr):
  if (1 <= chip_nr < 500000):
    return '12h'
  return '24h'


def get_delta(chip_nr, punch_time_value):
  format = get_format(chip_nr)
  value_range = format_value_range[format]
  assert punch_time_value < value_range
  seconds, centiseconds = divmod(punch_time_value, 100)
  return datetime.timedelta(seconds=seconds,
                            milliseconds=centiseconds*10)


def get_punch_timedelta(chip_nr, prev_time, delta):
  prev_date = datetime.datetime(prev_time.year,
                                prev_time.month,
                                prev_time.day)
  format_ = get_format(chip_nr)
  if format_ == '12h':
    if prev_time - prev_date < delta:
      return prev_date + delta
    elif prev_time - prev_date < delta + twelve_hours:
      return prev_date + twelve_hours + delta
    return prev_date + one_day + delta
  if format_ == '24h':
    if prev_time - prev_date < delta:
      return prev_date + delta
    return prev_date + one_day + delta


def get_chip_times(chip_nr, start_time, timedeltas):
  start_date = datetime.datetime(start_time.year,
      start_time.month, start_time.day)
  format_ = get_format(chip_nr)
  ref_time, step = start_date, one_day
  if format_ == '12h':
    step = twelve_hours
    if start_date + twelve_hours <= start_time:
      ref_time = start_date + step
  ref_delta = start_time - ref_time
  result = [None] * len(timedeltas)
  for i, delta in enumerate(timedeltas):
    if delta is None:
      continue
    if delta <= ref_delta:
      ref_time += step
    result[i] = ref_time + delta
    ref_delta = delta
  return result


def get_chip_start_time(chip_nr, start_time,
    chip_start_timedelta):
  start_date = datetime.datetime(start_time.year,
      start_time.month, start_time.day)
  format_ = get_format(chip_nr)
  ref_time, step = start_date, one_day
  if format_ == '12h':
    step = twelve_hours
    if start_date + twelve_hours <= start_time:
      ref_time = start_date + step
  candidates = [ref_time + m * step + chip_start_timedelta
      for m in range(-1, 2)]
  absdeltas = [abs(t - start_time) for t in candidates]
  mindelta = min(absdeltas)
  best_candidate_i = absdeltas.index(mindelta)
  return candidates[best_candidate_i]
