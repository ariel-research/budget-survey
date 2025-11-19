# Questions about MDSP Definition - Edge Case Handling

Hi [Researcher Name],

We're implementing the MDSP strategy from your paper and have a question about handling zero deviations.

## The Question

The MDSP definition requires that for every dimension j, either:
- `q1j - Pj > q2j - Pj > 0` (both above peak), OR  
- `q1j - Pj < q2j - Pj < 0` (both below peak)

**What should happen when one option is exactly at the peak (`d = 0`) in some dimensions while the other deviates?**

We're asking about two cases:
1. **Case 1**: `q_near` at peak (`d_near = 0`) while `q_far` deviates (`d_far ≠ 0`)
2. **Case 2**: `q_far` at peak (`d_far = 0`) while `q_near` deviates (`d_near ≠ 0`)

## Example 1: q_near at peak

**Peak**: `[50, 30, 20]`

- **q_near**: `[50, 35, 15]` → deviations: `[0, +5, -5]`
- **q_far**: `[55, 40, 10]` → deviations: `[+5, +10, -10]`

**Why it fails the strict definition:**

In dimension 1, `q_near` is at the peak (deviation = 0) while `q_far` deviates by +5. The MDSP condition requires:
- `(+5) > (0) > 0` → This fails because `0 > 0` is false
- `(+5) < (0) < 0` → This fails because `5 < 0` is false

So dimension 1 doesn't satisfy either condition, making the pair invalid under the strict definition.

**Why we think it should be valid:**

`q_near` is clearly closer overall (matches the ideal in dimension 1, and closer in dimensions 2 and 3). This still tests single-peaked preferences—users should prefer options that match their ideal.

## Example 2: q_far at peak

**Peak**: `[50, 30, 20]`

- **q_near**: `[55, 35, 15]` → deviations: `[+5, +5, -5]`
- **q_far**: `[50, 40, 10]` → deviations: `[0, +10, -10]`

In dimension 1, `q_far` is at the peak while `q_near` deviates by +5. This also fails the strict definition for the same reason. However, in this case `q_near` cannot be closer since `q_far` matches the ideal in dimension 1.

## Questions

1. Should pairs where `q_near` equals the peak in some dimensions (while `q_far` deviates) be considered valid MDSP tests? (Case 1: `d_near = 0`, `d_far ≠ 0`)
2. What about the reverse case where `q_far` equals the peak while `q_near` deviates? (Case 2: `d_far = 0`, `d_near ≠ 0`)
3. Is excluding zero deviations intentional, or should we interpret the definition more flexibly?
4. What's the intended behavior when comparing an option at the peak vs. one that deviates?

We've implemented an extended version that allows these cases, but want to confirm this aligns with your intended definition.

Thanks!

