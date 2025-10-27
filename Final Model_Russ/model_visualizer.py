import numpy as np
import plotly.graph_objects as go
from sklearn.metrics import precision_recall_curve

class ModelEvaluationVisualizer:
    """
    A class for creating interactive visualizations of model evaluation metrics.
    Currently supports precision-recall curves with threshold analysis.
    """
    
    def __init__(self, X, y):
        """
        Initialize the visualizer with feature data and true labels.
        
        Parameters:
        -----------
        X : array-like of shape (n_samples, n_features)
            The input samples
        y : array-like of shape (n_samples,)
            The true labels
        """
        self.X = X
        self.y = y
        
    def plot_precision_recall_curve(self, model, title=None, show_positive_predictions=True):
        """
        Create an interactive precision-recall curve plot using plotly.
        
        Parameters:
        -----------
        model : sklearn estimator
            Must implement predict_proba method
        title : str, optional
            Custom title for the plot
        show_positive_predictions : bool, default=True
            Whether to show the number of positive predictions in hover text
            
        Returns:
        --------
        plotly.graph_objects.Figure
            Interactive plot of precision-recall curve
        """
        # Get predicted probabilities for positive class
        y_probs = model.predict_proba(self.X)[:, 1]
        
        # Calculate precision and recall for different thresholds
        precision, recall, thresholds = precision_recall_curve(self.y, y_probs)
        
        # Create plotly figure
        fig = go.Figure()
        
        # Calculate hover text for positive predictions if requested
        hover_text = None
        if show_positive_predictions:
            positive_predictions = [(y_probs >= t).sum() for t in thresholds]
            hover_text = [f"Positive predictions: {pred}" for pred in positive_predictions]
        
        # Add traces for precision and recall
        fig.add_trace(go.Scatter(
            x=thresholds,
            y=precision[:-1],
            mode='lines',
            name='Precision',
            hovertemplate="Precision: %{y:.3f}<extra></extra>"
        ))

        fig.add_trace(go.Scatter(
            x=thresholds,
            y=recall[:-1],
            mode='lines',
            name='Recall',
            text=hover_text,
            hovertemplate="Recall: %{y:.3f}" +
                         ("<br>%{text}" if show_positive_predictions else "") +
                         "<extra></extra>"
        ))
        
        # Update layout
        fig.update_layout(
            title=title or 'Precision and Recall at Different Thresholds',
            xaxis_title='Threshold',
            yaxis_title='Score',
            hovermode='x unified',
            yaxis_range=[0, 1.05],
            xaxis_range=[-0.05, 1.05],
            legend=dict(
                yanchor="top",
                y=0.99,
                xanchor="left",
                x=0.01
            )
        )
        
        return fig
    

    def plot_positive_predictions(self, model, X_new, title=None):
        """
        Create an interactive plot showing the number of positive predictions at different thresholds
        and the estimated number of true positives based on precision from the test data.
        
        Parameters:
        -----------
        model : sklearn estimator
            Must implement predict_proba method
        X_new : array-like of shape (n_samples, n_features)
            The new input samples
        title : str, optional
            Custom title for the plot
            
        Returns:
        --------
        plotly.graph_objects.Figure
            Interactive plot of positive predictions and estimated true positives
        """
        # Get predicted probabilities for positive class on new data
        y_probs_new = model.predict_proba(X_new)[:, 1]
        
        # Use precision from the test data
        y_probs_test = model.predict_proba(self.X)[:, 1]
        precision, _, thresholds = precision_recall_curve(self.y, y_probs_test)
        
        # Calculate positive predictions and estimated true positives
        positive_predictions = [(y_probs_new >= t).sum() for t in thresholds]
        estimated_true_positives = [p * prec for p, prec in zip(positive_predictions, precision)]
        
        # Create plotly figure
        fig = go.Figure()
        
        # Add trace for positive predictions
        fig.add_trace(go.Scatter(
            x=thresholds,
            y=positive_predictions,
            mode='lines',
            name='Positive Predictions',
            hovertemplate="Positive Predictions: %{y}<br>Estimated True Positives: %{text:.2f}<br>Precision: %{customdata:.2%}<extra></extra>",
            text=estimated_true_positives,  # Add estimated true positives for hover text
            customdata=precision[:-1]  # Add precision for hover text
        ))
        # Update layout
        fig.update_layout(
            title=title or 'Positive Predictions at Different Thresholds',
            xaxis_title='Threshold',
            yaxis_title='Count',
            hovermode='x unified',
            yaxis_range=[0, max(positive_predictions) * 1.05],
            xaxis_range=[-0.05, 1.05],
            legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.01
            )
        )
        
        return fig
    def make_confusion_matrix(self, model, threshold=0.5):
        """
        Create a confusion matrix using the specified threshold.
        
        Parameters:
        -----------
        model : sklearn estimator
            Must implement predict_proba method
        threshold : float, default=0.5
            Threshold for converting probabilities to binary predictions
            
        Returns:
        --------
        array-like of shape (2, 2)
            Confusion matrix
        """
        y_pred = (model.predict_proba(self.X)[:, 1] >= threshold).astype(int)
        
        tp = ((y_pred == 1) & (self.y == 1)).sum()
        fp = ((y_pred == 1) & (self.y == 0)).sum()
        tn = ((y_pred == 0) & (self.y == 0)).sum()
        fn = ((y_pred == 0) & (self.y == 1)).sum()
        
        return np.array([[tn, fp], [fn, tp]])
        
    def find_optimal_threshold(self, model, criterion='f1'):
        """
        Find the optimal threshold based on various criteria.
        
        Parameters:
        -----------
        model : sklearn estimator
            Must implement predict_proba method
        criterion : str, default='f1'
            Criterion to optimize. Options: 'f1', 'balanced'
            
        Returns:
        --------
        float
            Optimal threshold value
        dict
            Metrics at optimal threshold
        """
        y_probs = model.predict_proba(self.X)[:, 1]
        precision, recall, thresholds = precision_recall_curve(self.y, y_probs)
        
        if criterion == 'f1':
            # Calculate F1 score for each threshold
            f1_scores = 2 * (precision[:-1] * recall[:-1]) / (precision[:-1] + recall[:-1])
            optimal_idx = np.nanargmax(f1_scores)
            
        elif criterion == 'balanced':
            # Find threshold where precision and recall are most similar
            differences = np.abs(precision[:-1] - recall[:-1])
            optimal_idx = np.argmin(differences)
        
        else:
            raise ValueError("Unsupported criterion. Use 'f1' or 'balanced'")
            
        optimal_threshold = thresholds[optimal_idx]
        
        return optimal_threshold, {
            'threshold': optimal_threshold,
            'precision': precision[optimal_idx],
            'recall': recall[optimal_idx]
        }