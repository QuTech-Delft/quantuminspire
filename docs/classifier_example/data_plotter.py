from sklearn.datasets import load_iris
from sklearn import preprocessing
import matplotlib.pyplot as plt
import numpy as np
from random import sample

plt.style.use('seaborn-whitegrid')


def get_bin(x, n):
    return format(int(x), 'b').zfill(n)


class DataPlotter:

    @staticmethod
    def plot_original_data(data1, data2):
        # Plot original data:
        plt.rcParams['figure.figsize'] = [8, 6]
        plt.scatter(data1[0], data1[1], alpha=0.8, s=10, c='red')   # Scatter plot data class 1
        plt.scatter(data2[0], data2[1], alpha=0.8, s=10, c='blue')  # Scatter plot data class 2
        plt.xlabel("Sepal length (cm)")  # x-label
        plt.ylabel("Sepal width (cm)")   # y-label
        plt.xlim(-1, 8)  # x-range
        plt.ylim(-1, 5)  # y-range
        plt.legend(["Iris Setosa", "Iris Versicolor"])
        fig = plt
        return fig

    @staticmethod
    def plot_standardised_data(data1, data2):
        plt.rcParams['figure.figsize'] = [8, 6]  # Plot size
        unit_circle = plt.Circle((0, 0), 1, color='grey', alpha=0.2, fill=False)  # Circle

        plt.scatter(data1[0], data1[1], alpha=0.8, s=10, c='red')   # Scatter plot data class 1
        plt.scatter(data2[0], data2[1], alpha=0.8, s=10, c='blue')  # Scatter plot data class 2
        plt.xlabel("Sepal length (cm)")  # x-label
        plt.ylabel("Sepal width (cm)")   # y-label
        plt.xlim(-2.5, 2.5)  # x-range
        plt.ylim(-2.5, 2.5)  # y-range
        fig = plt.gcf()  # unit circle plotting
        ax = fig.gca()
        ax.add_artist(unit_circle)
        plt.legend(["Iris Setosa", "Iris Versicolor"])
        plt.show()

    @staticmethod
    def plot_normalised_data(data1, data2):
        # Scatter plot normalised data
        plt.rcParams['figure.figsize'] = [8, 6]  # Plot size
        unit_circle = plt.Circle((0, 0), 1, color='grey', alpha=0.2, fill=False)  # Circle

        plt.scatter(data1[0], data1[1], alpha=0.8, s=10, c='red')   # Scatter plot data class 1
        plt.scatter(data2[0], data2[1], alpha=0.8, s=10, c='blue')  # Scatter plot data class 2
        plt.xlabel("Sepal length (cm)")  # x-label
        plt.ylabel("Sepal width (cm)")   # y-label
        plt.xlim(-2.5, 2.5)  # x-range
        plt.ylim(-2.5, 2.5)  # y-range

        fig = plt.gcf()  # unit circle plotting
        ax = fig.gca()
        ax.add_artist(unit_circle)
        plt.legend(["Iris Setosa", "Iris Versicolor"])
        # plt.show()

    @staticmethod
    def load_data(max_features=2):
        iris = load_iris()
        features = iris.data.T
        if max_features > 4:
            print("Error, maximum is 4 features in Iris data set")
        # Default: only the first two features of the data set
        data = [el[0:100] for el in features][0:max_features]
        half_len_data = len(data[0]) // 2
        # Rescale the data
        features_scaled = [preprocessing.scale(el) for el in data]
        iris_setosa_scaled = [el[0:half_len_data] for el in features_scaled]
        iris_versicolor_scaled = [el[half_len_data:] for el in features_scaled]

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

        iris_setosa_normalised = normalise_data(*iris_setosa_scaled)
        iris_versicolor_normalised = normalise_data(*iris_versicolor_scaled)
        return iris_setosa_normalised, iris_versicolor_normalised

    def plot_data_points(self, test_data, data_label0, data_label1, results):
        # Scatter plot full data set,test point and data points
        # Bar plot results (Project Q! ordering)

        plt.rcParams['figure.figsize'] = [16, 6]  # Plot size
        # load data:
        iris_setosa_normalised, iris_versicolor_normalised = self.load_data()

        # Scatter plot data points:
        plt.subplot(1, 2, 1)  # Scatter plot
        self.plot_normalised_data(iris_setosa_normalised, iris_versicolor_normalised)
        # Scatter plot data class ?
        plt.scatter(test_data[0], test_data[1], s=50, c='green')

        for data_point in data_label0:
            # Scatter plot data class 0
            plt.scatter(data_point[0], data_point[1], s=50, c='orange')
        for data_point in data_label1:
            # Scatter plot data class 1
            plt.scatter(data_point[0], data_point[1], s=50, c='orange')
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
        color_list = ['red', 'blue', 'red', 'blue', (0.1, 0.1, 0.1, 0.1),
                      (0.1, 0.1, 0.1, 0.1), (0.1, 0.1, 0.1, 0.1), (0.1, 0.1, 0.1, 0.1)]
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
        iris_setosa_normalised, iris_versicolor_normalised = self.load_data(max_features=features)

        random_label = 0
        data_label0 = []  # iris_setosa_normalised  # Label 0
        data_label1 = []  # iris_versicolor_normalised  # Label 1
        # Not strictly necessary but for educational purposed we don't want coinciding data points
        coinciding_data = True
        while coinciding_data:
            coinciding_data = False
            # Find index values
            random_label = sample([1, 0], 1)[0]
            len_label0 = int(size / 2 + 1 - random_label)
            len_label1 = int(size / 2 + random_label)

            index_label0 = sample(range(50), len_label0)
            index_label1 = sample(range(50), len_label1)

            # Find data points
            data_label0 = []  # iris_setosa_normalised  # Label 0
            data_label1 = []  # iris_versicolor_normalised  # Label 1

            for data_point in index_label0:
                data_label0.append([feature[data_point] for feature in iris_setosa_normalised])
            for data_point in index_label1:
                data_label1.append([feature[data_point] for feature in iris_versicolor_normalised])

            for i in range(len(data_label0)):
                for j in range(i + 1, len(data_label0)):
                    if data_label0[i] == data_label0[j]:
                        print("Coinciding data point found, restart")
                        coinciding_data = True

            for i in range(len(data_label1)):
                for j in range(i + 1, len(data_label1)):
                    if data_label1[i] == data_label1[j]:
                        print("Coinciding data point found, restart")
                        coinciding_data = True

        if random_label:
            test_data = data_label1.pop()
        else:
            test_data = data_label0.pop()

        return data_label0, data_label1, test_data, random_label

    def plot_data_points_multiple_features(self, data_label0, data_label1, test_data, random_label, results):
        # Scatter plot full data set, test point and data points for all combinations of features
        # Bar plot results (Project Q! ordering)

        # For now only 2 data points, 4 features

        # Load data:
        iris_setosa_normalised, iris_versicolor_normalised = self.load_data(max_features=4)

        # Find index of data points:
        def find_idx(needle, hay):
            for idx in range(len(hay[0])):
                if hay[0][idx] == needle[0] and hay[1][idx] == needle[1] and hay[2][idx] == needle[2]\
                        and hay[3][idx] == needle[3]:
                    return idx
            return "Data not found"

        idx_data_label0 = find_idx(data_label0[0], iris_setosa_normalised)
        idx_data_label1 = find_idx(data_label1[0], iris_versicolor_normalised)
        if random_label == 0:
            hay_test_data = iris_setosa_normalised
        else:
            hay_test_data = iris_versicolor_normalised
        idx_test_data = find_idx(test_data, hay_test_data)

        plt.rcParams['figure.figsize'] = [16, 6]  # Plot size

        plt.subplot2grid((2, 6), (0, 0))
        # load data:
        iris_setosa_normalised, iris_versicolor_normalised = self.load_data_selected_features(0, 1)
        # Scatter plot data points:
        self.plot_normalised_data(iris_setosa_normalised, iris_versicolor_normalised)

        # Scatter plot data
        if random_label == 0:
            test_data = iris_setosa_normalised
        else:
            test_data = iris_versicolor_normalised
        plt.scatter(test_data[0][idx_test_data], test_data[1][idx_test_data], s=50, c='green')
        plt.scatter(iris_setosa_normalised[0][idx_data_label0],
                    iris_setosa_normalised[1][idx_data_label0], s=50, c='orange')
        plt.scatter(iris_versicolor_normalised[0][idx_data_label1],
                    iris_versicolor_normalised[1][idx_data_label1], s=50, c='orange')
        plt.xlabel("Sepal length (cm)")  # x-label
        plt.ylabel("Sepal width (cm)")   # y-label

        plt.subplot2grid((2, 6), (0, 1))
        # load data:
        iris_setosa_normalised, iris_versicolor_normalised = self.load_data_selected_features(0, 2)
        # Scatter plot data points:
        self.plot_normalised_data(iris_setosa_normalised, iris_versicolor_normalised)
        # Scatter plot data
        if random_label == 0:
            test_data = iris_setosa_normalised
        else:
            test_data = iris_versicolor_normalised
        plt.scatter(test_data[0][idx_test_data], test_data[1][idx_test_data], s=50, c='green')
        plt.scatter(iris_setosa_normalised[0][idx_data_label0],
                    iris_setosa_normalised[1][idx_data_label0], s=50, c='orange')
        plt.scatter(iris_versicolor_normalised[0][idx_data_label1],
                    iris_versicolor_normalised[1][idx_data_label1], s=50, c='orange')
        plt.xlabel("Sepal length (cm)")  # x-label
        plt.ylabel("Petal length (cm)")  # y-label

        plt.subplot2grid((2, 6), (0, 2))
        # load data:
        iris_setosa_normalised, iris_versicolor_normalised = self.load_data_selected_features(0, 3)
        # Scatter plot data points:
        self.plot_normalised_data(iris_setosa_normalised, iris_versicolor_normalised)
        # Scatter plot data
        if random_label == 0:
            test_data = iris_setosa_normalised
        else:
            test_data = iris_versicolor_normalised
        plt.scatter(test_data[0][idx_test_data], test_data[1][idx_test_data], s=50, c='green')
        plt.scatter(iris_setosa_normalised[0][idx_data_label0],
                    iris_setosa_normalised[1][idx_data_label0], s=50, c='orange')
        plt.scatter(iris_versicolor_normalised[0][idx_data_label1],
                    iris_versicolor_normalised[1][idx_data_label1], s=50, c='orange')
        plt.xlabel("Sepal length (cm)")  # x-label
        plt.ylabel("Petal width (cm)")   # y-label

        plt.subplot2grid((2, 6), (1, 0))
        # load data:
        iris_setosa_normalised, iris_versicolor_normalised = self.load_data_selected_features(1, 2)
        # Scatter plot data points:
        self.plot_normalised_data(iris_setosa_normalised, iris_versicolor_normalised)
        # Scatter plot data
        if random_label == 0:
            test_data = iris_setosa_normalised
        else:
            test_data = iris_versicolor_normalised
        plt.scatter(test_data[0][idx_test_data], test_data[1][idx_test_data], s=50, c='green')
        plt.scatter(iris_setosa_normalised[0][idx_data_label0],
                    iris_setosa_normalised[1][idx_data_label0], s=50, c='orange')
        plt.scatter(iris_versicolor_normalised[0][idx_data_label1],
                    iris_versicolor_normalised[1][idx_data_label1], s=50, c='orange')
        plt.xlabel("Sepal width (cm)")   # x-label
        plt.ylabel("Petal length (cm)")  # y-label

        plt.subplot2grid((2, 6), (1, 1))
        # load data:
        iris_setosa_normalised, iris_versicolor_normalised = self.load_data_selected_features(1, 3)
        # Scatter plot data points:
        self.plot_normalised_data(iris_setosa_normalised, iris_versicolor_normalised)
        # Scatter plot data
        if random_label == 0:
            test_data = iris_setosa_normalised
        else:
            test_data = iris_versicolor_normalised
        plt.scatter(test_data[0][idx_test_data], test_data[1][idx_test_data], s=50, c='green')
        plt.scatter(iris_setosa_normalised[0][idx_data_label0],
                    iris_setosa_normalised[1][idx_data_label0], s=50, c='orange')
        plt.scatter(iris_versicolor_normalised[0][idx_data_label1],
                    iris_versicolor_normalised[1][idx_data_label1], s=50, c='orange')
        plt.xlabel("Sepal width (cm)")  # x-label
        plt.ylabel("Petal width (cm)")  # y-label

        plt.subplot2grid((2, 6), (1, 2))
        # load data:
        iris_setosa_normalised, iris_versicolor_normalised = self.load_data_selected_features(2, 3)
        # Scatter plot data points:
        self.plot_normalised_data(iris_setosa_normalised, iris_versicolor_normalised)
        # Scatter plot data
        if random_label == 0:
            test_data = iris_setosa_normalised
        else:
            test_data = iris_versicolor_normalised
        plt.scatter(test_data[0][idx_test_data], test_data[1][idx_test_data], s=50, c='green')
        plt.scatter(iris_setosa_normalised[0][idx_data_label0],
                    iris_setosa_normalised[1][idx_data_label0], s=50, c='orange')
        plt.scatter(iris_versicolor_normalised[0][idx_data_label1],
                    iris_versicolor_normalised[1][idx_data_label1], s=50, c='orange')
        plt.xlabel("Petal length (cm)")  # x-label
        plt.ylabel("Petal width (cm)")   # y-label

        # Bar plot results:
        plt.subplot2grid((2, 6), (0, 3), colspan=2, rowspan=3)
        size = len(list(results.keys())[0])
        res = [get_bin(el, size) for el in range(2 ** size)]
        prob = [0] * 2**size
        for key, value in results.items():
            prob[int(key, 2)] = value

        # Set color=light grey when 2nd qubit = 1
        # Set color=blue when 2nd qubit = 0, and last qubit = 1
        # Set color=red when 2nd qubit = 0, and last qubit = 0
        color_list = ['red', 'blue', 'red', 'blue', 'red', 'blue', 'red', 'blue',
                      (0.1, 0.1, 0.1, 0.1), (0.1, 0.1, 0.1, 0.1), (0.1, 0.1, 0.1, 0.1), (0.1, 0.1, 0.1, 0.1),
                      (0.1, 0.1, 0.1, 0.1), (0.1, 0.1, 0.1, 0.1), (0.1, 0.1, 0.1, 0.1), (0.1, 0.1, 0.1, 0.1)]
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
        iris_setosa_scaled = [el[0:half_len_data] for el in features_scaled]
        iris_versicolor_scaled = [el[half_len_data:] for el in features_scaled]

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

        iris_setosa_normalised = normalise_data(*iris_setosa_scaled)
        iris_versicolor_normalised = normalise_data(*iris_versicolor_scaled)
        return iris_setosa_normalised, iris_versicolor_normalised

    @staticmethod
    def true_classifier(data_label0, data_label1, test_data):
        label0 = 0
        label1 = 0
        for element in data_label0:
            label0 += np.linalg.norm(np.array(element) - np.array(test_data))
        for element in data_label1:
            label1 += np.linalg.norm(np.array(element) - np.array(test_data))
        if label0 > label1:
            return 1
        return 0

    def quality_classifier(self, input_size, input_features, sample_size):
        correct = 0
        wrong = 0
        for idx in range(sample_size):
            data_label0, data_label1, test_data, random_label = self.grab_random_data(size=input_size,
                                                                                      features=input_features)
            prediction = self.true_classifier(data_label0, data_label1, test_data)
            if prediction == random_label:
                correct += 1
            else:
                wrong += 1
        return correct/sample_size, wrong/sample_size
