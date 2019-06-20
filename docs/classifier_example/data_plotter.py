from sklearn.datasets import load_iris
from sklearn import preprocessing
import matplotlib.pyplot as plt
import numpy as np
from random import sample, randint

plt.style.use('seaborn-whitegrid')


def get_bin(x, n): return format(int(x), 'b').zfill(n)


class DataPlotter():
    def __init__(self):
        pass

    @staticmethod
    def plot_original_data(data1, data2):
        # Plot original data:
        plt.rcParams['figure.figsize'] = [8, 6]
        plt.scatter(data1[0], data1[1], alpha=0.8, s=10,
                    c='red')  # Scatter plot data class 1
        plt.scatter(data2[0], data2[1], alpha=0.8, s=10,
                    c='blue')  # Scatter plot data class 2
        plt.xlabel("Sepal length (cm)")  # x-label
        plt.ylabel("Sepal width (cm)")  # y-lable
        plt.xlim(-1, 8)  # x-range
        plt.ylim(-1, 5)  # y-range
        plt.legend(["Iris Setosa", "Iris Versicolor"])
        fig = plt
        return fig

    @staticmethod
    def plot_standardised_data(data1, data2):
        plt.rcParams['figure.figsize'] = [8, 6]  # Plot size
        unitcircle = plt.Circle((0, 0), 1, color='grey',
                                alpha=0.2, fill=False)  # Circle

        plt.scatter(data1[0], data1[1], alpha=0.8, s=10,
                    c='red')  # Scatter plot data class 1
        plt.scatter(data2[0], data2[1], alpha=0.8, s=10,
                    c='blue')  # Scatter plot data class 2
        plt.xlabel("Sepal length (cm)")  # x-label
        plt.ylabel("Sepal width (cm)")  # y-lable
        plt.xlim(-2.5, 2.5)  # x-range
        plt.ylim(-2.5, 2.5)  # y-range
        fig = plt.gcf()  # unit circle plotting
        ax = fig.gca()
        ax.add_artist(unitcircle)
        plt.legend(["Iris Setosa", "Iris Versicolor"])
        plt.show

    @staticmethod
    def plot_normalised_data(data1, data2):
        # Scatter plot normalised data
        plt.rcParams['figure.figsize'] = [8, 6]  # Plot size
        unitcircle = plt.Circle((0, 0), 1, color='grey',
                                alpha=0.2, fill=False)  # Circle

        plt.scatter(data1[0], data1[1], alpha=0.8, s=10,
                    c='red')  # Scatter plot data class 1
        plt.scatter(data2[0], data2[1], alpha=0.8, s=10,
                    c='blue')  # Scatter plot data class 2
        plt.xlabel("Sepal length (cm)")  # x-label
        plt.ylabel("Sepal width (cm)")  # y-lable
        plt.xlim(-2.5, 2.5)  # x-range
        plt.ylim(-2.5, 2.5)  # y-range

        fig = plt.gcf()  # unit circle plotting
        ax = fig.gca()
        ax.add_artist(unitcircle)
        plt.legend(["Iris Setosa", "Iris Versicolor"])

    @staticmethod
    def load_data(max_features=2):
        iris = load_iris()
        features = iris.data.T
        if max_features > 4:
            print("Error, maximum is 4 features in Iris data set")
        # Default: only the first two features of the dataset
        data = [el[0:100] for el in features][0:max_features]
        half_len_data = len(data[0]) // 2
        # Rescale the data
        features_scaled = [preprocessing.scale(el) for el in data]
        Iris_setosa_scaled = [el[0:half_len_data] for el in features_scaled]
        Iris_versicolor_scaled = [el[half_len_data:] for el in features_scaled]

        # Normalise the data
        def normalise_data(*args):
            """Normalise data to unit length
                input: *args, arrays of same length
                output: normalised *args
            """
            for idx in range(len(args[0])):
                norm = 0
                for arg in args:
                    norm += arg[idx]**2
                norm **= (1 / 2)
                for arg in args:
                    arg[idx] /= norm
            return args

        Iris_setosa_normalised = normalise_data(*Iris_setosa_scaled)
        Iris_versicolor_normalised = normalise_data(*Iris_versicolor_scaled)
        return Iris_setosa_normalised, Iris_versicolor_normalised

    def plot_data_points(self, TestData, Datalabel0, Datalabel1, results):
        # Scatter plot full data set,test point and data points
        # Bar plot results (Project Q! ordering)

        plt.rcParams['figure.figsize'] = [16, 6]  # Plot size
        # load data:
        Iris_setosa_normalised, Iris_versicolor_normalised = self.load_data()

        # Scatter plot data points:
        plt.subplot(1, 2, 1)  # Scatter plot
        self.plot_normalised_data(
            Iris_setosa_normalised, Iris_versicolor_normalised)
        # Scatter plot data class ?
        plt.scatter(TestData[0], TestData[1], s=50, c='green')

        for data_point in Datalabel0:
            # Scatter plot data class 0
            plt.scatter(data_point[0], data_point[1],  s=50, c='orange')
        for data_point in Datalabel1:
            # Scatter plot data class 1
            plt.scatter(data_point[0], data_point[1],  s=50, c='orange')
        plt.legend(["Iris Setosa (label 0)",
                    "Iris Versicolor (label 1)", "Test point", "Data points"])

        # Bar plot results:
        plt.subplot(1, 2, 2)  # Bar plot
        size = len(list(results.keys())[0])
        res = [get_bin(el, size) for el in range(2 ** size)]
        prob = [0] * 2**size
        for key, value in results.items():
            prob[int(key, 2)] = value

        # Set color=light grey when 2nd qubit = 1
        # Set color=blue when 2nd qubit = 0, and last qubit = 1
        # Set color=red when 2nd qubit = 0, and last qubit = 0
        color_list = ['red', 'blue', 'red', 'blue', (0.1, 0.1, 0.1, 0.1), (
            0.1, 0.1, 0.1, 0.1), (0.1, 0.1, 0.1, 0.1), (0.1, 0.1, 0.1, 0.1)]
        plt.bar(res, prob, color=color_list)
        plt.ylabel('Probability')
        plt.title('Results')
        plt.ylim(0, .5)
        plt.xticks(rotation='vertical')
        return prob

    def grab_random_data(self, size=4, features=2):
        """Grabs random points from Iris set of which:
        size/2 points of label 0
        size/2 points of label 1
        1 point of label random"""

        if size % 2 != 0:
            return "Size must be an even number"

        # load data:
        Iris_setosa_normalised, Iris_versicolor_normalised = self.load_data(
            max_features=features)

        # Not strictly necessary but for educational purposed we don't want coinciding data points
        coinciding_data = True
        while coinciding_data:
            coinciding_data = False
            # Find index values
            random_label = sample([1, 0], 1)[0]
            len_lable0 = int(size / 2 + 1 - random_label)
            len_label1 = int(size / 2 + random_label)

            index_label0 = sample(range(50), len_lable0)
            index_label1 = sample(range(50), len_label1)

            # Find data points
            Datalabel0 = []  # Iris_setosa_normalised  # Label 0
            Datalabel1 = []  # Iris_versicolor_normalised  # Label 1

            for datapoint in index_label0:
                Datalabel0.append([feature[datapoint]
                                   for feature in Iris_setosa_normalised])
            for datapoint in index_label1:
                Datalabel1.append([feature[datapoint]
                                   for feature in Iris_versicolor_normalised])

            for i in range(len(Datalabel0)):
                for j in range(i + 1, len(Datalabel0)):
                    if Datalabel0[i] == Datalabel0[j]:
                        print("Coinciding data point found, restart")
                        coinciding_data = True

            for i in range(len(Datalabel1)):
                for j in range(i + 1, len(Datalabel1)):
                    if Datalabel1[i] == Datalabel1[j]:
                        print("Coinciding data point found, restart")
                        coinciding_data = True

        if random_label:
            TestData = Datalabel1.pop()
        else:
            TestData = Datalabel0.pop()

        return Datalabel0, Datalabel1, TestData, random_label

    def plot_data_points_multiple_features(self, Datalabel0, Datalabel1, TestData, random_label, results):
        # Scatter plot full data set, test point and data points for all combinations of features
        # Bar plot results (Project Q! ordering)

        # For now only 2 data points, 4 features

        # Load data:
        Iris_setosa_normalised, Iris_versicolor_normalised = self.load_data(
            max_features=4)

        # Find index of data points:
        def find_idx(needle, hay):
            for idx in range(len(hay[0])):
                if hay[0][idx] == needle[0] and hay[1][idx] == needle[1] and hay[2][idx] == needle[2] and hay[3][idx] == needle[3]:
                    return idx
            return "Data not found"

        idxDatalabel0 = find_idx(Datalabel0[0], Iris_setosa_normalised)
        idxDatalabel1 = find_idx(Datalabel1[0], Iris_versicolor_normalised)
        if random_label == 0:
            hay_TestData = Iris_setosa_normalised
        else:
            hay_TestData = Iris_versicolor_normalised
        idxTestData = find_idx(TestData, hay_TestData)

        plt.rcParams['figure.figsize'] = [16, 6]  # Plot size

        ax1 = plt.subplot2grid((2, 6), (0, 0))
        # load data:
        Iris_setosa_normalised, Iris_versicolor_normalised = self.load_data_selected_features(
            0, 1)
        # Scatter plot data points:
        self.plot_normalised_data(
            Iris_setosa_normalised, Iris_versicolor_normalised)

        # Scatter plot data
        if random_label == 0:
            testdata = Iris_setosa_normalised
        else:
            testdata = Iris_versicolor_normalised
        plt.scatter(testdata[0][idxTestData], testdata[1]
                    [idxTestData], s=50, c='green')
        plt.scatter(Iris_setosa_normalised[0][idxDatalabel0],
                    Iris_setosa_normalised[1][idxDatalabel0],  s=50, c='orange')
        plt.scatter(Iris_versicolor_normalised[0][idxDatalabel1],
                    Iris_versicolor_normalised[1][idxDatalabel1],  s=50, c='orange')
        plt.xlabel("Sepal length (cm)")  # x-label
        plt.ylabel("Sepal width (cm)")  # y-lable

        ax2 = plt.subplot2grid((2, 6), (0, 1))
        # load data:
        Iris_setosa_normalised, Iris_versicolor_normalised = self.load_data_selected_features(
            0, 2)
        # Scatter plot data points:
        self.plot_normalised_data(
            Iris_setosa_normalised, Iris_versicolor_normalised)
        # Scatter plot data
        if random_label == 0:
            testdata = Iris_setosa_normalised
        else:
            testdata = Iris_versicolor_normalised
        plt.scatter(testdata[0][idxTestData], testdata[1]
                    [idxTestData], s=50, c='green')
        plt.scatter(Iris_setosa_normalised[0][idxDatalabel0],
                    Iris_setosa_normalised[1][idxDatalabel0],  s=50, c='orange')
        plt.scatter(Iris_versicolor_normalised[0][idxDatalabel1],
                    Iris_versicolor_normalised[1][idxDatalabel1],  s=50, c='orange')
        plt.xlabel("Sepal length (cm)")  # x-label
        plt.ylabel("Petal length (cm)")  # y-lable

        ax3 = plt.subplot2grid((2, 6), (0, 2))
        # load data:
        Iris_setosa_normalised, Iris_versicolor_normalised = self.load_data_selected_features(
            0, 3)
        # Scatter plot data points:
        self.plot_normalised_data(
            Iris_setosa_normalised, Iris_versicolor_normalised)
        # Scatter plot data
        if random_label == 0:
            testdata = Iris_setosa_normalised
        else:
            testdata = Iris_versicolor_normalised
        plt.scatter(testdata[0][idxTestData], testdata[1]
                    [idxTestData], s=50, c='green')
        plt.scatter(Iris_setosa_normalised[0][idxDatalabel0],
                    Iris_setosa_normalised[1][idxDatalabel0],  s=50, c='orange')
        plt.scatter(Iris_versicolor_normalised[0][idxDatalabel1],
                    Iris_versicolor_normalised[1][idxDatalabel1],  s=50, c='orange')
        plt.xlabel("Sepal length (cm)")  # x-label
        plt.ylabel("Petal width (cm)")  # y-lable

        ax4 = plt.subplot2grid((2, 6), (1, 0))
        # load data:
        Iris_setosa_normalised, Iris_versicolor_normalised = self.load_data_selected_features(
            1, 2)
        # Scatter plot data points:
        self.plot_normalised_data(
            Iris_setosa_normalised, Iris_versicolor_normalised)
        # Scatter plot data
        if random_label == 0:
            testdata = Iris_setosa_normalised
        else:
            testdata = Iris_versicolor_normalised
        plt.scatter(testdata[0][idxTestData], testdata[1]
                    [idxTestData], s=50, c='green')
        plt.scatter(Iris_setosa_normalised[0][idxDatalabel0],
                    Iris_setosa_normalised[1][idxDatalabel0],  s=50, c='orange')
        plt.scatter(Iris_versicolor_normalised[0][idxDatalabel1],
                    Iris_versicolor_normalised[1][idxDatalabel1],  s=50, c='orange')
        plt.xlabel("Sepal width (cm)")  # y-lable
        plt.ylabel("Petal length (cm)")  # y-lable

        ax5 = plt.subplot2grid((2, 6), (1, 1))
        # load data:
        Iris_setosa_normalised, Iris_versicolor_normalised = self.load_data_selected_features(
            1, 3)
        # Scatter plot data points:
        self.plot_normalised_data(
            Iris_setosa_normalised, Iris_versicolor_normalised)
        # Scatter plot data
        if random_label == 0:
            testdata = Iris_setosa_normalised
        else:
            testdata = Iris_versicolor_normalised
        plt.scatter(testdata[0][idxTestData], testdata[1]
                    [idxTestData], s=50, c='green')
        plt.scatter(Iris_setosa_normalised[0][idxDatalabel0],
                    Iris_setosa_normalised[1][idxDatalabel0],  s=50, c='orange')
        plt.scatter(Iris_versicolor_normalised[0][idxDatalabel1],
                    Iris_versicolor_normalised[1][idxDatalabel1],  s=50, c='orange')
        plt.xlabel("Sepal width (cm)")  # y-lable
        plt.ylabel("Petal width (cm)")  # y-lable

        ax6 = plt.subplot2grid((2, 6), (1, 2))
        # load data:
        Iris_setosa_normalised, Iris_versicolor_normalised = self.load_data_selected_features(
            2, 3)
        # Scatter plot data points:
        self.plot_normalised_data(
            Iris_setosa_normalised, Iris_versicolor_normalised)
        # Scatter plot data
        if random_label == 0:
            testdata = Iris_setosa_normalised
        else:
            testdata = Iris_versicolor_normalised
        plt.scatter(testdata[0][idxTestData], testdata[1]
                    [idxTestData], s=50, c='green')
        plt.scatter(Iris_setosa_normalised[0][idxDatalabel0],
                    Iris_setosa_normalised[1][idxDatalabel0],  s=50, c='orange')
        plt.scatter(Iris_versicolor_normalised[0][idxDatalabel1],
                    Iris_versicolor_normalised[1][idxDatalabel1],  s=50, c='orange')
        plt.xlabel("Petal length (cm)")  # x-label
        plt.ylabel("Petal width (cm)")  # y-lable

        # Bar plot results:
        ax7 = plt.subplot2grid((2, 6), (0, 3), colspan=2, rowspan=3)
        size = len(list(results.keys())[0])
        res = [get_bin(el, size) for el in range(2 ** size)]
        prob = [0] * 2**size
        for key, value in results.items():
            prob[int(key, 2)] = value

        # Set color=light grey when 2nd qubit = 1
        # Set color=blue when 2nd qubit = 0, and last qubit = 1
        # Set color=red when 2nd qubit = 0, and last qubit = 0
        color_list = ['red', 'blue', 'red', 'blue', 'red', 'blue', 'red', 'blue', (0.1, 0.1, 0.1, 0.1), (
            0.1, 0.1, 0.1, 0.1), (0.1, 0.1, 0.1, 0.1), (0.1, 0.1, 0.1, 0.1), (0.1, 0.1, 0.1, 0.1), (
            0.1, 0.1, 0.1, 0.1), (0.1, 0.1, 0.1, 0.1), (0.1, 0.1, 0.1, 0.1)]
        plt.bar(res, prob, color=color_list)
        plt.ylabel('Probability')
        plt.title('Results')
        plt.ylim(0, .5)
        plt.xticks(rotation='vertical')
        return plt.show()

    @staticmethod
    def load_data_selected_features(feature1, feature2):
        iris = load_iris()
        features = iris.data.T
        data = [el[0:100] for el in features][0:4]
        data = [data[feature1], data[feature2]]
        half_len_data = len(data[0]) // 2
        # Rescale the data
        features_scaled = [preprocessing.scale(el) for el in data]
        Iris_setosa_scaled = [el[0:half_len_data] for el in features_scaled]
        Iris_versicolor_scaled = [el[half_len_data:] for el in features_scaled]

        # Normalise the data
        def normalise_data(*args):
            """Normalise data to unit length
                input: *args, arrays of same length
                output: normalised *args
            """
            for idx in range(len(args[0])):
                norm = 0
                for arg in args:
                    norm += arg[idx]**2
                norm **= (1 / 2)
                for arg in args:
                    arg[idx] /= norm
            return args

        Iris_setosa_normalised = normalise_data(*Iris_setosa_scaled)
        Iris_versicolor_normalised = normalise_data(*Iris_versicolor_scaled)
        return Iris_setosa_normalised, Iris_versicolor_normalised

    @staticmethod
    def true_classifier(Datalabel0, Datalabel1, TestData):
        label0 = 0
        label1 = 0
        for element in Datalabel0:
            label0 += np.linalg.norm(np.array(element) - np.array(TestData))
        for element in Datalabel1:
            label1 += np.linalg.norm(np.array(element) - np.array(TestData))
        if label0 > label1:
            return 1
        return 0

    def quality_classifier(self, input_size, input_features, sample_size):
        correct = 0
        wrong = 0
        for idx in range(sample_size):
            Datalabel0, Datalabel1, TestData, random_label = self.grab_random_data(
                size=input_size, features=input_features)
            prediction = self.true_classifier(Datalabel0, Datalabel1, TestData)
            if prediction == random_label:
                correct += 1
            else:
                wrong += 1
        return correct/sample_size, wrong/sample_size
