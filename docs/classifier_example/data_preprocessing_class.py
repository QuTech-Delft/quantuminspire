from sklearn.datasets import load_iris
from sklearn import preprocessing
import matplotlib.pyplot as plt
import numpy as np

plt.style.use('seaborn-whitegrid')



def preproccessdata(data, display_fig=True, axislimits=[None, None, None]):
    """Function to plot procedure of preprocessing data

    Arguments:
        data {list} -- data of class 1 and -1 appended:
             [data_feature1, data_feature2, name_feature1, name_feature2]

    Keyword Arguments:
        axislimits {list} -- Optional axis limits (default: {[None, None, None]})
        Example input: axislimits = [[(-1, 8), (-1, 5)], [(-2.5, 2.5), (-2.5, 2.5)], [(-2.5, 2.5), (-2.5, 2.5)]]

    Returns:
        list -- list of normalised data class 1 and data class -1
        fig  -- figure of preprocessed data
    """
    half_len_data = len(data[0]) // 2
    data1 = [el[0:half_len_data] for el in data[0:2]]
    data2 = [el[half_len_data:-1] for el in data[0:2]]

    # Circle
    unitcircle1 = plt.Circle((0, 0), 1, color='grey', alpha=0.2, fill=False)
    unitcircle2 = plt.Circle((0, 0), 1, color='grey', alpha=0.2, fill=False)
    unitcircle3 = plt.Circle((0, 0), 1, color='grey', alpha=0.2, fill=False)

    # Plot original data:
    plt.subplot(1, 3, 1)
    plt.scatter(data1[0], data1[1], alpha=0.8, s=10, c='red')  # Scatter plot data class 1
    plt.scatter(data2[0], data2[1], alpha=0.8, s=10, c='blue')  # Scatter plot data class 2
    plt.xlabel(data[2])  # x-label
    plt.ylabel(data[3])  # y-lable
    if axislimits[0] is not None:
        plt.xlim(axislimits[0][0])  # x-range
        plt.ylim(axislimits[0][1])  # y-range

    fig = plt.gcf()  # unit circle plotting
    ax = fig.gca()
    ax.add_artist(unitcircle1)


    # Rescale whole data-set to have zero mean and unit variance
    features_scaled = [preprocessing.scale(el) for el in data[0:2]]
    data1_scaled = [el[0:half_len_data] for el in features_scaled]
    data2_scaled = [el[half_len_data:-1] for el in features_scaled]

    plt.subplot(1, 3, 2)
    plt.scatter(data1_scaled[0], data1_scaled[1], alpha=0.8, s=10, c='red')  # Scatter plot data class 1
    plt.scatter(data2_scaled[0], data2_scaled[1], alpha=0.8, s=10, c='blue')  # Scatter plot data class 2
    plt.xlabel(data[2])  # x-label
    plt.ylabel(data[3])  # y-label
    if axislimits[0] is not None:
        plt.xlim(axislimits[1][0])  # x-range
        plt.ylim(axislimits[1][1])  # y-range

    fig = plt.gcf()  # unit circle plotting
    ax = fig.gca()
    ax.add_artist(unitcircle2)


    # Normalisation to the unit circle

    def normalise_data(arr1, arr2):
        """Normalise data to unit length
            input: two array same length
            output: normalised arrays
        """
        for idx in range(len(arr1)):
            norm = (arr1[idx]**2 + arr2[idx]**2)**(1 / 2)
            arr1[idx] = arr1[idx] / norm
            arr2[idx] = arr2[idx] / norm
        return [arr1, arr2]


    data1_normalised = normalise_data(data1_scaled[0], data1_scaled[1])
    data2_normalised = normalise_data(data2_scaled[0], data2_scaled[1])

    # Scatter plot normalised data
    plt.subplot(1, 3, 3)
    plt.scatter(data1_normalised[0], data1_normalised[1], alpha=0.8, s=10, c='red')  # Scatter plot data class 1
    plt.scatter(data2_normalised[0], data2_normalised[1], alpha=0.8, s=10, c='blue')  # Scatter plot data class 2
    plt.xlabel(data[2])  # x-label
    plt.ylabel(data[3])  # y-label
    if axislimits[2] is not None:
        plt.xlim(axislimits[2][0])  # x-range
        plt.ylim(axislimits[2][1])  # y-range

    fig = plt.gcf()  # unit circle plotting
    ax = fig.gca()
    ax.add_artist(unitcircle3)


    # Display final plot
    if display_fig:
        plt.show()

    zippeddata1 = list(zip(data1_normalised[0], data1_normalised[1]))
    zippeddata2 = list(zip(data2_normalised[0], data2_normalised[1]))

    return plt, zippeddata1, zippeddata2

if __name__ == "__main__":
    # Load some test data:
    iris = load_iris()
    features = iris.data.T

    data = [el[0:100] for el in features][0:2]

    data.append("Sepal Length (cm)")
    data.append("Sepal width (cm)")

    print("Example for the Iris test data based on first two features:")
    class1, class2 = preproccessdata(data, display_fig=True, axislimits=[[(-1, 8), (-1, 5)], [(-2.5, 2.5), (-2.5, 2.5)], [(-2.5, 2.5), (-2.5, 2.5)]])


class DataPlotter():
    def __init__(self):
        pass

    def plot_original_data(self, data1, data2):
        # Plot original data:
        plt.rcParams['figure.figsize'] = [8, 6]
        plt.scatter(data1[0], data1[1], alpha=0.8, s=10, c='red')  # Scatter plot data class 1
        plt.scatter(data2[0], data2[1], alpha=0.8, s=10, c='blue')  # Scatter plot data class 2
        plt.xlabel("Sepal length (cm)")  # x-label
        plt.ylabel("Sepal width (cm)")  # y-lable
        plt.xlim(-1, 8)  # x-range
        plt.ylim(-1, 5)  # y-range
        plt.legend(["Iris Setosa", "Iris Versicolor"])
        fig = plt
        return fig

    def plot_standarised_data(self, data1, data2):
        plt.rcParams['figure.figsize'] = [8, 6]  # Plot size
        unitcircle = plt.Circle((0, 0), 1, color='grey', alpha=0.2, fill=False)  # Circle

        plt.scatter(data1[0], data1[1], alpha=0.8, s=10, c='red')  # Scatter plot data class 1
        plt.scatter(data2[0], data2[1], alpha=0.8, s=10, c='blue')  # Scatter plot data class 2
        plt.xlabel("Sepal length (cm)")  # x-label
        plt.ylabel("Sepal width (cm)")  # y-lable
        plt.xlim(-2.5, 2.5)  # x-range
        plt.ylim(-2.5, 2.5)  # y-range
        fig = plt.gcf()  # unit circle plotting
        ax = fig.gca()
        ax.add_artist(unitcircle)
        plt.legend(["Iris Setosa", "Iris Versicolor"])
        plt.show

    def plot_normalised_data(self, data1, data2):
        # Scatter plot normalised data
        plt.rcParams['figure.figsize'] = [8, 6]  # Plot size
        unitcircle = plt.Circle((0, 0), 1, color='grey', alpha=0.2, fill=False)  # Circle

        plt.scatter(data1[0], data1[1], alpha=0.8, s=10, c='red')  # Scatter plot data class 1
        plt.scatter(data2[0], data2[1], alpha=0.8, s=10, c='blue')  # Scatter plot data class 2
        plt.xlabel("Sepal length (cm)")  # x-label
        plt.ylabel("Sepal width (cm)")  # y-lable
        plt.xlim(-2.5, 2.5)  # x-range
        plt.ylim(-2.5, 2.5)  # y-range

        fig = plt.gcf()  # unit circle plotting
        ax = fig.gca()
        ax.add_artist(unitcircle)
        plt.legend(["Iris Setosa", "Iris Versicolor"])
        plt.show
        plt



