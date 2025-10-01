from typing import List
import matplotlib.pyplot as plt

def plot_recall_curve(recall: List[float], precision: List[float], title: str = "Recall Curve") -> None:
    plt.figure(figsize=(8, 6))
    plt.plot(recall, precision, marker='o')
    plt.title(title)
    plt.xlabel('Recall')
    plt.ylabel('Precision')
    plt.grid()
    plt.xlim([0.0, 1.0])
    plt.ylim([0.0, 1.0])
    plt.axhline(y=0.5, color='r', linestyle='--')
    plt.axvline(x=0.5, color='r', linestyle='--')
    plt.show()