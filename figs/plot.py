import matplotlib.pyplot as plt
import numpy as np

# Data for the bar plot
categories = ['Gemma 3 1B', 'Gemma 3 4B']
anls_1B = np.array([0.455,0.154,0.605])
anls_4B = np.array([0.789, 0.721, 0.939])
values = [anls_1B.mean(), anls_4B.mean()]

plt.figure(figsize=(8, 6))
# Create the bar plot
plt.bar(categories, values, color=['blue', 'orange'])
# for i, v in enumerate(values):
#     plt.text(i, v + 0.02, f'{v:.2f}', ha='center', fontsize=20)

plt.ylabel('ANLS')
#plt.title('Comparison of ANLS over the model size')
plt.ylim([0, 1])

plt.savefig("figs/gemma_size_comparison_meta.pdf")
plt.show()


