from evals.scorer import _values_equal

# delivered: ground truth 4.16, model computed 4.155716524320005
print(_values_equal(4.16, 4.155716524320005))  # should now be True
print(_values_equal(4.16, 5.0))  # should still be False - sanity check
