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


def get_punch_timedelta(prev_time, chip_nr, delta):
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
