from metric_learn import SCML
import numpy as np

triplets = np.array([[[1.2, 7.5], [1.3, 1.5], [6.2, 9.7]],
            [[1.3, 4.5], [3.2, 4.6], [5.4, 5.4]],
            [[3.2, 7.5], [3.3, 1.5], [8.2, 9.7]],
            [[3.3, 4.5], [5.2, 4.6], [7.4, 5.4]]])

scml = SCML()

result = scml.fit(triplets)
print(result)
