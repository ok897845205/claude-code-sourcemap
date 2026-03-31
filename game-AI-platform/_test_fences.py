import sys
sys.path.insert(0, ".")
from src.pipeline.code_gen import _strip_fences

# Test 1: trailing fence only
test1 = "import X;\nexport default Y;\n```"
r1 = _strip_fences(test1)
print("Test 1 (trailing fence):", repr(r1[-30:]))
assert "```" not in r1, f"FAIL: trailing ``` not removed! Got: {r1[-30:]}"

# Test 2: both fences
test2 = "```javascript\nimport X;\nexport default Y;\n```"
r2 = _strip_fences(test2)
print("Test 2 (both fences):", repr(r2[-30:]))
assert "```" not in r2, f"FAIL: fences not removed!"

# Test 3: no fences
test3 = "import X;\nexport default Y;"
r3 = _strip_fences(test3)
print("Test 3 (no fences):", repr(r3[-30:]))
assert r3 == test3

# Test 4: fence with trailing whitespace
test4 = "import X;\nexport default Y;\n```\n  "
r4 = _strip_fences(test4)
print("Test 4 (fence + trailing ws):", repr(r4[-30:]))
assert "```" not in r4, f"FAIL: trailing ``` not removed!"

print("\nAll tests passed!")
