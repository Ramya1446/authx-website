"""
Comprehensive Evaluation Framework for Enhanced AI Tampering Detection
Generates quantitative metrics required for academic publication
"""

import numpy as np
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, confusion_matrix, classification_report
)
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List, Tuple
import time
import json
from pathlib import Path
import pandas as pd

class TamperingDetectionEvaluator:
    """
    Evaluator for AI tampering detection system
    Provides comprehensive quantitative metrics for research papers
    """
    
    def __init__(self, detector):
        """
        Args:
            detector: Instance of EnhancedAITamperingDetector
        """
        self.detector = detector
        self.results = {
            'predictions': [],
            'ground_truth': [],
            'probabilities': [],
            'latencies': [],
            'content_types': []
        }
        
    def evaluate_dataset(self, 
                        real_images: List[bytes],
                        fake_images: List[bytes],
                        content_type: str = "image/jpeg") -> Dict:
        """
        Evaluate detector on a dataset of real and AI-generated images
        
        Args:
            real_images: List of real image bytes
            fake_images: List of AI-generated image bytes
            content_type: MIME type of content
            
        Returns:
            Dictionary containing all evaluation metrics
        """
        print(f"Evaluating on {len(real_images)} real and {len(fake_images)} fake images...")
        
        # Process real images
        for img_bytes in real_images:
            start_time = time.time()
            result = self.detector.analyze(img_bytes, content_type)
            latency = time.time() - start_time
            
            self.results['predictions'].append(result['tamper_probability'] > 0.5)
            self.results['ground_truth'].append(False)  # Real = not tampered
            self.results['probabilities'].append(result['tamper_probability'])
            self.results['latencies'].append(latency)
            self.results['content_types'].append(content_type)
        
        # Process fake images
        for img_bytes in fake_images:
            start_time = time.time()
            result = self.detector.analyze(img_bytes, content_type)
            latency = time.time() - start_time
            
            self.results['predictions'].append(result['tamper_probability'] > 0.5)
            self.results['ground_truth'].append(True)  # Fake = tampered
            self.results['probabilities'].append(result['tamper_probability'])
            self.results['latencies'].append(latency)
            self.results['content_types'].append(content_type)
        
        return self.compute_metrics()
    
    def compute_metrics(self) -> Dict:
        """
        Compute comprehensive quantitative metrics
        
        Returns:
            Dictionary with all metrics needed for paper
        """
        y_true = np.array(self.results['ground_truth'])
        y_pred = np.array(self.results['predictions'])
        y_prob = np.array(self.results['probabilities'])
        
        # Core classification metrics
        accuracy = accuracy_score(y_true, y_pred)
        precision = precision_score(y_true, y_pred, zero_division=0)
        recall = recall_score(y_true, y_pred, zero_division=0)
        f1 = f1_score(y_true, y_pred, zero_division=0)
        
        # Handle case where all predictions are same class
        try:
            auc_roc = roc_auc_score(y_true, y_prob)
        except:
            auc_roc = 0.5  # Random classifier
        
        # Confusion matrix
        tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()
        
        # Specificity (True Negative Rate)
        specificity = tn / (tn + fp) if (tn + fp) > 0 else 0
        
        # False Positive Rate and False Negative Rate
        fpr = fp / (fp + tn) if (fp + tn) > 0 else 0
        fnr = fn / (fn + tp) if (fn + tp) > 0 else 0
        
        # Performance metrics
        avg_latency = np.mean(self.results['latencies'])
        std_latency = np.std(self.results['latencies'])
        
        metrics = {
            # Classification Performance
            'accuracy': round(accuracy * 100, 2),
            'precision': round(precision * 100, 2),
            'recall': round(recall * 100, 2),
            'f1_score': round(f1 * 100, 2),
            'auc_roc': round(auc_roc, 4),
            'specificity': round(specificity * 100, 2),
            
            # Error Rates
            'false_positive_rate': round(fpr * 100, 2),
            'false_negative_rate': round(fnr * 100, 2),
            
            # Confusion Matrix Components
            'true_positives': int(tp),
            'true_negatives': int(tn),
            'false_positives': int(fp),
            'false_negatives': int(fn),
            
            # Performance
            'avg_latency_ms': round(avg_latency * 1000, 2),
            'std_latency_ms': round(std_latency * 1000, 2),
            'throughput_images_per_sec': round(1.0 / avg_latency, 2),
            
            # Dataset Info
            'total_samples': len(y_true),
            'real_samples': int(np.sum(y_true == False)),
            'fake_samples': int(np.sum(y_true == True))
        }
        
        return metrics
    
    def evaluate_by_modality(self,
                            datasets: Dict[str, Tuple[List[bytes], List[bytes]]]) -> Dict:
        """
        Evaluate across different content modalities
        
        Args:
            datasets: Dict mapping content_type to (real_samples, fake_samples)
            
        Returns:
            Per-modality metrics
        """
        results = {}
        
        for content_type, (real_samples, fake_samples) in datasets.items():
            # Reset results for this modality
            self.results = {
                'predictions': [],
                'ground_truth': [],
                'probabilities': [],
                'latencies': [],
                'content_types': []
            }
            
            metrics = self.evaluate_dataset(real_samples, fake_samples, content_type)
            results[content_type] = metrics
            
        return results
    
    def evaluate_with_thresholds(self, 
                                thresholds: List[float],
                                real_images: List[bytes],
                                fake_images: List[bytes],
                                content_type: str = "image/jpeg") -> pd.DataFrame:
        """
        Evaluate performance across different decision thresholds
        
        Args:
            thresholds: List of threshold values to test
            real_images: Real image samples
            fake_images: Fake image samples
            content_type: Content MIME type
            
        Returns:
            DataFrame with metrics for each threshold
        """
        # Get all probabilities first
        probabilities = []
        ground_truth = []
        
        for img_bytes in real_images:
            result = self.detector.analyze(img_bytes, content_type)
            probabilities.append(result['tamper_probability'])
            ground_truth.append(False)
        
        for img_bytes in fake_images:
            result = self.detector.analyze(img_bytes, content_type)
            probabilities.append(result['tamper_probability'])
            ground_truth.append(True)
        
        probabilities = np.array(probabilities)
        ground_truth = np.array(ground_truth)
        
        # Evaluate at each threshold
        results = []
        for threshold in thresholds:
            predictions = probabilities > threshold
            
            acc = accuracy_score(ground_truth, predictions)
            prec = precision_score(ground_truth, predictions, zero_division=0)
            rec = recall_score(ground_truth, predictions, zero_division=0)
            f1 = f1_score(ground_truth, predictions, zero_division=0)
            
            tn, fp, fn, tp = confusion_matrix(ground_truth, predictions).ravel()
            fpr = fp / (fp + tn) if (fp + tn) > 0 else 0
            
            results.append({
                'threshold': threshold,
                'accuracy': acc * 100,
                'precision': prec * 100,
                'recall': rec * 100,
                'f1_score': f1 * 100,
                'fpr': fpr * 100
            })
        
        return pd.DataFrame(results)
    
    def compare_with_baseline(self,
                             baseline_results: Dict,
                             our_results: Dict) -> pd.DataFrame:
        """
        Create comparison table with baseline methods
        
        Args:
            baseline_results: Dict of {method_name: metrics_dict}
            our_results: Our method's metrics
            
        Returns:
            Comparison DataFrame
        """
        comparison = []
        
        # Add baseline methods
        for method_name, metrics in baseline_results.items():
            comparison.append({
                'Method': method_name,
                'Accuracy (%)': metrics.get('accuracy', 0),
                'Precision (%)': metrics.get('precision', 0),
                'Recall (%)': metrics.get('recall', 0),
                'F1-Score (%)': metrics.get('f1_score', 0),
                'Latency (ms)': metrics.get('avg_latency_ms', 0)
            })
        
        # Add our method
        comparison.append({
            'Method': 'Authx (Ours)',
            'Accuracy (%)': our_results['accuracy'],
            'Precision (%)': our_results['precision'],
            'Recall (%)': our_results['recall'],
            'F1-Score (%)': our_results['f1_score'],
            'Latency (ms)': our_results['avg_latency_ms']
        })
        
        return pd.DataFrame(comparison)
    
    def plot_confusion_matrix(self, save_path: str = None):
        """Generate confusion matrix visualization"""
        y_true = np.array(self.results['ground_truth'])
        y_pred = np.array(self.results['predictions'])
        
        cm = confusion_matrix(y_true, y_pred)
        
        plt.figure(figsize=(8, 6))
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
                   xticklabels=['Real', 'Fake'],
                   yticklabels=['Real', 'Fake'])
        plt.ylabel('True Label')
        plt.xlabel('Predicted Label')
        plt.title('Confusion Matrix - AI Tampering Detection')
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
    
    def plot_roc_curve(self, save_path: str = None):
        """Generate ROC curve"""
        from sklearn.metrics import roc_curve
        
        y_true = np.array(self.results['ground_truth'])
        y_prob = np.array(self.results['probabilities'])
        
        fpr, tpr, thresholds = roc_curve(y_true, y_prob)
        auc = roc_auc_score(y_true, y_prob)
        
        plt.figure(figsize=(8, 6))
        plt.plot(fpr, tpr, linewidth=2, label=f'ROC Curve (AUC = {auc:.4f})')
        plt.plot([0, 1], [0, 1], 'k--', linewidth=1, label='Random Classifier')
        plt.xlabel('False Positive Rate')
        plt.ylabel('True Positive Rate')
        plt.title('ROC Curve - AI Tampering Detection')
        plt.legend()
        plt.grid(alpha=0.3)
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
    
    def generate_latex_table(self, metrics: Dict) -> str:
        """Generate LaTeX table for paper"""
        latex = """
\\begin{table}[h]
\\centering
\\caption{Performance Metrics of Enhanced AI Tampering Detection}
\\label{tab:performance}
\\begin{tabular}{lr}
\\hline
\\textbf{Metric} & \\textbf{Value} \\\\
\\hline
Accuracy & {accuracy}\\% \\\\
Precision & {precision}\\% \\\\
Recall & {recall}\\% \\\\
F1-Score & {f1_score}\\% \\\\
AUC-ROC & {auc_roc} \\\\
Specificity & {specificity}\\% \\\\
\\hline
False Positive Rate & {false_positive_rate}\\% \\\\
False Negative Rate & {false_negative_rate}\\% \\\\
\\hline
Avg. Latency & {avg_latency_ms} ms \\\\
Throughput & {throughput_images_per_sec} img/s \\\\
\\hline
\\end{tabular}
\\end{table}
""".format(**metrics)
        
        return latex
    
    def export_results(self, output_dir: str):
        """Export all results and visualizations"""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        # Compute metrics
        metrics = self.compute_metrics()
        
        # Save metrics as JSON
        with open(output_path / 'metrics.json', 'w') as f:
            json.dump(metrics, f, indent=2)
        
        # Save as CSV for easy import
        pd.DataFrame([metrics]).to_csv(output_path / 'metrics.csv', index=False)
        
        # Generate plots
        self.plot_confusion_matrix(str(output_path / 'confusion_matrix.png'))
        self.plot_roc_curve(str(output_path / 'roc_curve.png'))
        
        # Generate LaTeX table
        latex_table = self.generate_latex_table(metrics)
        with open(output_path / 'table.tex', 'w') as f:
            f.write(latex_table)
        
        # Save detailed classification report
        y_true = np.array(self.results['ground_truth'])
        y_pred = np.array(self.results['predictions'])
        report = classification_report(y_true, y_pred, 
                                       target_names=['Real', 'Fake'])
        with open(output_path / 'classification_report.txt', 'w') as f:
            f.write(report)
        
        print(f"✅ Results exported to {output_dir}/")
        print(f"   - metrics.json: All metrics in JSON format")
        print(f"   - metrics.csv: Metrics in CSV format")
        print(f"   - confusion_matrix.png: Confusion matrix plot")
        print(f"   - roc_curve.png: ROC curve plot")
        print(f"   - table.tex: LaTeX table for paper")
        print(f"   - classification_report.txt: Detailed report")
        
        return metrics


# Example usage and dataset recommendations
"""
RECOMMENDED DATASETS FOR EVALUATION:

1. CIFAKE Dataset (Easy to access)
   - 60,000 real images from CIFAR-10
   - 60,000 AI-generated images
   - Download: https://www.kaggle.com/datasets/birdy654/cifake-real-and-ai-generated-synthetic-images

2. DiffusionDB
   - 2 million AI-generated images
   - Multiple models (Stable Diffusion, DALL-E, etc.)
   - Download: https://github.com/poloclub/diffusiondb

3. RAISE Dataset (Real images)
   - 8,156 high-quality camera photos
   - Download: http://loki.disi.unitn.it/RAISE/

4. ForenSynths
   - ProGAN, StyleGAN, StyleGAN2 generated images
   - Download: https://github.com/peterwang512/CNNDetection

EXAMPLE USAGE:

from ai_detector import EnhancedAITamperingDetector
from evaluation_framework import TamperingDetectionEvaluator

# Initialize
detector = EnhancedAITamperingDetector()
evaluator = TamperingDetectionEvaluator(detector)

# Load your dataset
real_images = load_real_images()  # Your function to load real images
fake_images = load_fake_images()  # Your function to load AI-generated images

# Evaluate
metrics = evaluator.evaluate_dataset(real_images, fake_images)

# Export results
evaluator.export_results('evaluation_results')

# Print summary
print(f"Accuracy: {metrics['accuracy']}%")
print(f"Precision: {metrics['precision']}%")
print(f"Recall: {metrics['recall']}%")
print(f"F1-Score: {metrics['f1_score']}%")
"""