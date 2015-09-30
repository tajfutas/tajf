import datetime

STRP_ISO_FMT = '%Y-%m-%dT%H:%M:%S.%f'
STRP_ISO_FMT2 = '%Y-%m-%dT%H:%M:%S'


def string_to_datetime(s):
  try:
    return datetime.datetime.strptime(s_hstart, STRP_ISO_FMT)
  except ValueError:
    return datetime.datetime.strptime(s_hstart, STRP_ISO_FMT2)


def string_to_timedelta(s):
  if s is None:
    errfstr = 'invaild timedelta string: {!r}'
    raise ValueError(errfstr.format(s))
  restr = ('^(?P<minutes>\d+)?:?(?P<seconds>\d+)?'
           '\.?(?P<prec_value>\d+)?$')
  m = re.search(restr, s)
  if m is None:
    errfstr = 'invaild timedelta string: {!r}'
    raise ValueError(errfstr.format(s))
  d = {k: int(v) for k, v in m.groupdict().items() if v}
  s_prec_value = m.group('prec_value')
  if s_prec_value:
    preceision = len(s_prec_value)
    µs = d['prec_value'] * 10**(6-preceision)
    d['microseconds'] = µs
    del d['prec_value']
  return datetime.timedelta(**d)


def seq_of_strings_to_timedelta(seq):
  result = []
  for s in seq:
    try:
      td = string_to_timedelta(s)
    except ValueError:
      break
    else:
      result.append(td)
  return result


def timedelta_to_milliseconds(td):
    return (td.days * 86400000 + td.seconds * 1000
        + round(td.microseconds/ 1000))


# based on source code of datetime.py
def timedelta_to_string(td, precision=0):
    mm, ss = divmod(td.seconds, 60)
    if td.days:
      mm += 24 * 60 * td.days
    if mm:
      s = '{:d}:{:0>2d}'.format(mm, ss)
    else:
      s = '{:d}'.format(ss)
    if precision:
      fs = '.{{:0<{:d}d}}'.format(precision)
      value = round(td.microseconds / 10**(6-precision))
      s += fs.format(value)
    return s
