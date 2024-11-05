from metric_learn import SCML
import numpy as np

triplets = [[[1.2, 3.2], [2.3, 5.5], [2.1, 0.6]],
            [[4.5, 2.3], [2.1, 2.3], [7.3, 3.4]]]

scml = SCML(random_state=42,n_basis=160)
result = scml.fit(triplets)
print(result)

triplets_test = np.array(
[[[5.6, 5.3], [2.2, 2.1], [1.2, 3.4]],
 [[6.0, 4.2], [4.3, 1.2], [0.1, 7.8]]])
print(scml.predict(triplets_test))

