def validate(course_controls, punch_controls):
  result = [None] * len(course_controls)
  pi = 0
  for i, course_control in enumerate(course_controls):
    for j, punch_control in enumerate(punch_controls[pi:]):
      if punch_control == course_control:
        pi += j
        result[i] = pi
        break
    else:
      break
  return result
