import numpy as np
from sklearn.cluster import HDBSCAN
from sklearn.neighbors import NearestNeighbors
import matplotlib.pyplot as plt
from sklearn.preprocessing import MinMaxScaler

class ClusteringManager:
    """
    Handles all clustering-related functionality:
      - Grid downsampling
      - HDBSCAN clustering
      - Assigning clusters
      - Plotting clusters
    """

    def __init__(self, cell_size, distance_threshold, min_cluster_size):
        self.cell_size = cell_size
        self.distance_threshold = distance_threshold
        self.min_cluster_size = min_cluster_size

    def grid_sample(self, points_array):
        """
        Downsamples points using a grid of a given cell size.
        
        Args:
            points_array (np.ndarray): An array of shape (n_points, 2) containing x, y coordinates.
        
        Returns:
            A dictionary mapping grid cell indices to the index of the first point encountered in that cell.
        """
        cell_indices_x = np.floor(points_array[:, 0] / self.cell_size)
        cell_indices_y = np.floor(points_array[:, 1] / self.cell_size)
        cell_indices = list(zip(cell_indices_x, cell_indices_y))
        
        cell_dict = {}
        for idx, cell in enumerate(cell_indices):
            if cell not in cell_dict:
                cell_dict[cell] = idx  # keep the first point for each cell
        return cell_dict

    def perform_clustering(self, sampled_points, all_points):
        """
        Performs HDBSCAN clustering on the sampled_points and then assigns each point in all_points
        the label of its nearest neighbor (if within distance_threshold); otherwise, label as noise (-1).
        
        Args:
            sampled_points (np.ndarray): Downsampled points used for clustering.
            all_points (np.ndarray): All data points.
        
        Returns:
            A numpy array of final cluster labels.
        """
        # In edge cases, min_cluster_size might be bigger than the sample itself
        actual_min_cluster_size = min(self.min_cluster_size, len(sampled_points))

        clusterer = HDBSCAN(min_cluster_size=actual_min_cluster_size)
        clusterer.fit(sampled_points)
        sampled_labels = clusterer.labels_
        num_clusters = len(np.unique(sampled_labels)) - 1  # subtract 1 for noise

        # Arbitrary safeguard: if too many clusters, skip
        if num_clusters > 500:
            return None
        
        nn_model = NearestNeighbors(n_neighbors=1)
        nn_model.fit(sampled_points)
        distances, indices = nn_model.kneighbors(all_points)
        nearest_labels = sampled_labels[indices.flatten()]
        final_labels = np.where(distances.flatten() <= self.distance_threshold, nearest_labels, -1)
        return final_labels

    def cluster_space(self, df, x, y):
        """
        Clusters the DataFrame based on the provided x and y columns.
        Adds the 'Cluster_ID' column.
        
        Args:
            df (DataFrame): DataFrame containing at least the columns x, y, and "pcf_key".
            x (str): Name of the first metric (x coordinate).
            y (str): Name of the second metric (y coordinate).
            
        Returns:
            A copy of the DataFrame with Cluster_IDs assigned or None if clustering fails.
        """
        points = df[[x, y]].values
        cell_dict = self.grid_sample(points)
        sampled_indices = list(cell_dict.values())
        sampled_points = points[sampled_indices]

        labels = self.perform_clustering(sampled_points, points)
        if labels is None:
            return None

        df_copy = df.copy()
        df_copy['Cluster_ID'] = labels
        return df_copy

    def plot_clusters(self, df, x, y):
        """
        Creates a scatter plot of the clusters using x and y as coordinates.
        Annotates points having a related constant and marks centroids.
        
        Args:
            df (DataFrame): DataFrame containing x, y, Cluster_ID, and related_objects.
            x (str): Name of the x coordinate column.
            y (str): Name of the y coordinate column.
        
        Returns:
            (fig, ax): The matplotlib figure and axes objects.
        """
        points = df[[x, y]].values
        cluster_ids = df['Cluster_ID'].values
        related_constants = df['related_objects'].values
        
        unique_labels = np.unique(cluster_ids)
        # For color mapping
        if unique_labels.max() != -1:
            normalized_labels = MinMaxScaler(feature_range=(0, 1)).fit_transform(cluster_ids.reshape(-1, 1)).flatten()
        else:
            normalized_labels = cluster_ids
        
        cmap = plt.get_cmap("tab20", len(unique_labels))
        colors = [
            cmap(normalized_labels[i])[:3] if cluster_ids[i] != -1 else (0.5, 0.5, 0.5)
            for i in range(len(cluster_ids))
        ]
        
        fig, ax = plt.subplots(figsize=(12, 8))
        ax.scatter(points[:, 0], points[:, 1], color=colors, s=10, alpha=0.8)
        
        # Annotate anchor points
        for xi, yi, const in zip(points[:, 0], points[:, 1], related_constants):
            if const is not None and const != []:
                ax.scatter(xi, yi, s=10, color='red', alpha=0.8)
                ax.text(xi, yi, str(const), fontsize=8, ha='left', va='bottom', color='blue')
        
        # Plot cluster centroids (ignoring noise)
        centroids = df[df['Cluster_ID'] != -1].groupby('Cluster_ID')[[x, y]].mean()
        for cid, row in centroids.iterrows():
            ax.scatter(row[x], row[y], color='black', s=20, edgecolors='white')
        
        ax.set_xlabel(x)
        ax.set_ylabel(y)
        ax.set_title('Clusters with Cluster IDs and Related Constants')
        ax.grid(False)
        return fig, ax