"""
Authx Real Testing Suite
Collect actual performance data from your system for research paper
Modified for fake/real folder structure
"""

import os
import time
import json
import requests
from pathlib import Path
import numpy as np
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix, roc_curve, auc, classification_report
)
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime

# ============================================================================
# CONFIGURATION
# ============================================================================
API_BASE_URL = "http://127.0.0.1:8000"
TEST_DATASET_DIR = "test_dataset"
RESULTS_DIR = "real_results"
MAX_SAMPLES_PER_CLASS = 1000  # Limit per class to avoid too many requests

os.makedirs(RESULTS_DIR, exist_ok=True)

# ============================================================================
# 1. TEST DATA COLLECTION
# ============================================================================
class AuthxTester:
    """Collect real performance metrics from Authx system"""
    
    def __init__(self):
        self.results = {
            "registration_tests": [],
            "verification_tests": [],
            "performance_metrics": [],
            "detection_scores": []
        }
    
    def test_registration(self, file_path, true_label, content_info):
        """
        Test single file registration
        
        Args:
            file_path: Path to test file
            true_label: "real" or "fake"
            content_info: dict with metadata
        """
        start_time = time.time()
        
        try:
            with open(file_path, 'rb') as f:
                files = {'file': f}
                data = {
                    'owner_name': 'Test User',
                    'owner_address': '0xTest',
                    'content_type': content_info.get('type', 'image/jpeg'),
                    'description': f"Test: {true_label}",
                    'ai_tool': content_info.get('ai_tool', '')
                }
                
                response = requests.post(
                    f"{API_BASE_URL}/register",
                    files=files,
                    data=data,
                    timeout=30
                )
                
                processing_time = time.time() - start_time
                
                result = {
                    "file_name": os.path.basename(file_path),
                    "true_label": true_label,
                    "status": response.status_code,
                    "response": response.json() if response.status_code == 200 else None,
                    "processing_time": processing_time,
                    "file_size": os.path.getsize(file_path),
                    "content_info": content_info
                }
                
                if response.status_code == 200:
                    proof = response.json().get('proof', {})
                    tamper_score = proof.get('tamper_score', 0)
                    result["tamper_score"] = tamper_score
                    
                    # Predicted label based on tamper score
                    # Higher score = more likely to be fake/AI-modified
                    result["predicted_label"] = "fake" if tamper_score > 0.5 else "real"
                    
                    # Extract detection details
                    tampering_analysis = proof.get('tampering_analysis', {})
                    result["detection_details"] = tampering_analysis.get('analysis_details', {})
                
                self.results["registration_tests"].append(result)
                return result
                
        except Exception as e:
            print(f"Error testing {file_path}: {e}")
            result = {
                "file_name": os.path.basename(file_path),
                "true_label": true_label,
                "status": "error",
                "error": str(e),
                "processing_time": time.time() - start_time,
                "file_size": os.path.getsize(file_path) if os.path.exists(file_path) else 0
            }
            self.results["registration_tests"].append(result)
            return None
    
    def run_batch_test(self, test_dataset_path, max_samples=MAX_SAMPLES_PER_CLASS):
        """
        Run tests on fake/real folder structure
        
        Expected folder structure:
        test_dataset/
        ├── fake/     (AI-generated or AI-modified images)
        └── real/     (Original/authentic images)
        """
        
        categories = {
            "fake": "fake",
            "real": "real"
        }
        
        total_tests = 0
        
        for category, true_label in categories.items():
            category_path = Path(test_dataset_path) / category
            
            if not category_path.exists():
                print(f"⚠️  Folder not found: {category_path}")
                continue
            
            # Get all image files
            files = []
            for ext in ['*.jpg', '*.jpeg', '*.png', '*.JPG', '*.JPEG', '*.PNG']:
                files.extend(list(category_path.glob(ext)))
            
            # Limit samples if needed
            if len(files) > max_samples:
                print(f"📊 Found {len(files)} files in {category}, using first {max_samples}")
                files = files[:max_samples]
            
            print(f"\n📁 Testing {category} ({len(files)} files)...")
            
            for idx, file_path in enumerate(files, 1):
                content_info = {
                    "type": "image/jpeg" if file_path.suffix.lower() in ['.jpg', '.jpeg'] else "image/png",
                    "category": category,
                    "ai_tool": self._extract_ai_tool(file_path.name)
                }
                
                result = self.test_registration(str(file_path), true_label, content_info)
                
                if result:
                    total_tests += 1
                    if idx % 50 == 0:  # Progress update every 50 files
                        print(f"  Progress: {idx}/{len(files)} files processed...")
                    elif idx % 10 == 0:
                        print(f"  ✓ Processed {idx} files...")
        
        print(f"\n✅ Completed {total_tests} tests")
        return total_tests
    
    def _extract_ai_tool(self, filename):
        """Extract AI tool from filename"""
        filename_lower = filename.lower()
        if "dalle" in filename_lower or "dall-e" in filename_lower:
            return "DALL-E"
        elif "midjourney" in filename_lower or "mj" in filename_lower:
            return "Midjourney"
        elif "stable" in filename_lower or "sd" in filename_lower or "stablediffusion" in filename_lower:
            return "Stable Diffusion"
        elif "gpt" in filename_lower or "chatgpt" in filename_lower:
            return "ChatGPT"
        return "Unknown AI"
    
    def calculate_metrics(self):
        """Calculate accuracy metrics from test results"""
        
        if not self.results["registration_tests"]:
            print("⚠️  No test results available!")
            return None
        
        y_true = []
        y_pred = []
        y_scores = []
        
        for test in self.results["registration_tests"]:
            if test.get("predicted_label") and test.get("status") == 200:
                # Convert to binary: 1 = fake, 0 = real
                y_true.append(1 if test["true_label"] == "fake" else 0)
                y_pred.append(1 if test["predicted_label"] == "fake" else 0)
                y_scores.append(test.get("tamper_score", 0))
        
        if not y_true:
            print("⚠️  No valid predictions to calculate metrics!")
            return None
        
        metrics = {
            "accuracy": accuracy_score(y_true, y_pred),
            "precision": precision_score(y_true, y_pred, zero_division=0),
            "recall": recall_score(y_true, y_pred, zero_division=0),
            "f1_score": f1_score(y_true, y_pred, zero_division=0),
            "confusion_matrix": confusion_matrix(y_true, y_pred).tolist(),
            "total_samples": len(y_true),
            "classification_report": classification_report(y_true, y_pred, 
                                                          target_names=["Real", "Fake"],
                                                          output_dict=True)
        }
        
        # ROC curve
        if len(set(y_true)) > 1:  # Need both classes
            fpr, tpr, thresholds = roc_curve(y_true, y_scores)
            roc_auc = auc(fpr, tpr)
            metrics["roc_curve"] = {
                "fpr": fpr.tolist(),
                "tpr": tpr.tolist(),
                "thresholds": thresholds.tolist(),
                "auc": roc_auc
            }
        
        # Calculate specificity and sensitivity
        tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()
        metrics["specificity"] = tn / (tn + fp) if (tn + fp) > 0 else 0
        metrics["sensitivity"] = tp / (tp + fn) if (tp + fn) > 0 else 0
        
        return metrics
    
    def save_results(self, filename="test_results.json"):
        """Save all results to JSON"""
        filepath = os.path.join(RESULTS_DIR, filename)
        
        # Calculate metrics
        metrics = self.calculate_metrics()
        
        output = {
            "timestamp": datetime.now().isoformat(),
            "total_tests": len(self.results["registration_tests"]),
            "successful_tests": len([t for t in self.results["registration_tests"] if t.get("status") == 200]),
            "metrics": metrics,
            "raw_results": self.results
        }
        
        with open(filepath, 'w') as f:
            json.dump(output, f, indent=2)
        
        print(f"💾 Results saved to: {filepath}")
        return filepath


# ============================================================================
# 2. REAL PLOTS FROM ACTUAL DATA
# ============================================================================
class RealPlotGenerator:
    """Generate plots from actual test results"""
    
    def __init__(self, results_file):
        with open(results_file, 'r') as f:
            self.data = json.load(f)
        
        self.metrics = self.data.get("metrics", {})
        self.raw_results = self.data.get("raw_results", {})
    
    def plot_all(self):
        """Generate all plots from real data"""
        plt.style.use('seaborn-v0_8-paper')
        
        print("\n📊 Generating plots from real data...")
        
        self.plot_confusion_matrix()
        self.plot_roc_curve()
        self.plot_detection_scores()
        self.plot_processing_time()
        self.plot_error_analysis()
        self.plot_score_distribution_by_class()
        
        print("✅ All plots generated!")
    
    def plot_confusion_matrix(self):
        """Real confusion matrix"""
        if not self.metrics or "confusion_matrix" not in self.metrics:
            print("⚠️  No confusion matrix data")
            return
        
        cm = np.array(self.metrics["confusion_matrix"])
        
        fig, ax = plt.subplots(figsize=(10, 8))
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
                    xticklabels=["Real", "Fake"],
                    yticklabels=["Real", "Fake"],
                    ax=ax, cbar_kws={'label': 'Count'})
        ax.set_xlabel('Predicted Label', fontsize=12, fontweight='bold')
        ax.set_ylabel('True Label', fontsize=12, fontweight='bold')
        ax.set_title(f'Confusion Matrix (n={self.metrics["total_samples"]})', 
                     fontsize=14, fontweight='bold', pad=20)
        
        # Add metrics text
        acc = self.metrics["accuracy"]
        f1 = self.metrics["f1_score"]
        prec = self.metrics["precision"]
        rec = self.metrics["recall"]
        text = f'Accuracy: {acc:.3f}\nPrecision: {prec:.3f}\nRecall: {rec:.3f}\nF1-Score: {f1:.3f}'
        ax.text(2.2, 0.5, text, fontsize=11, bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
        
        plt.tight_layout()
        plt.savefig(f'{RESULTS_DIR}/confusion_matrix.png', dpi=300, bbox_inches='tight')
        print("  ✓ Confusion matrix saved")
        plt.close()
    
    def plot_roc_curve(self):
        """Real ROC curve"""
        if not self.metrics or "roc_curve" not in self.metrics:
            print("⚠️  No ROC curve data")
            return
        
        roc = self.metrics["roc_curve"]
        fpr = roc["fpr"]
        tpr = roc["tpr"]
        roc_auc = roc["auc"]
        
        fig, ax = plt.subplots(figsize=(10, 8))
        ax.plot(fpr, tpr, 'b-', linewidth=3, label=f'Authx (AUC = {roc_auc:.3f})')
        ax.plot([0, 1], [0, 1], 'k--', alpha=0.5, linewidth=2, label='Random Classifier (AUC = 0.500)')
        ax.fill_between(fpr, tpr, alpha=0.3)
        ax.set_xlabel('False Positive Rate', fontsize=12, fontweight='bold')
        ax.set_ylabel('True Positive Rate', fontsize=12, fontweight='bold')
        ax.set_title('ROC Curve: AI-Generated/Modified Content Detection', 
                     fontsize=14, fontweight='bold', pad=20)
        ax.legend(loc='lower right', fontsize=11)
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.set_xlim([-0.01, 1.01])
        ax.set_ylim([-0.01, 1.01])
        
        plt.tight_layout()
        plt.savefig(f'{RESULTS_DIR}/roc_curve.png', dpi=300, bbox_inches='tight')
        print("  ✓ ROC curve saved")
        plt.close()
    
    def plot_detection_scores(self):
        """Distribution of detection scores"""
        tests = self.raw_results.get("registration_tests", [])
        
        if not tests:
            print("⚠️  No test data")
            return
        
        real_scores = [t["tamper_score"] for t in tests 
                       if t["true_label"] == "real" and t.get("status") == 200]
        fake_scores = [t["tamper_score"] for t in tests 
                       if t["true_label"] == "fake" and t.get("status") == 200]
        
        fig, ax = plt.subplots(figsize=(12, 7))
        
        ax.hist(real_scores, bins=30, alpha=0.7, label=f'Real Content (n={len(real_scores)})', 
                color='#2ecc71', edgecolor='black', linewidth=1.2)
        ax.hist(fake_scores, bins=30, alpha=0.7, label=f'Fake Content (n={len(fake_scores)})', 
                color='#e74c3c', edgecolor='black', linewidth=1.2)
        ax.axvline(x=0.5, color='black', linestyle='--', linewidth=2.5, 
                   label='Decision Threshold (0.5)')
        
        ax.set_xlabel('Tampering/AI Detection Score', fontsize=12, fontweight='bold')
        ax.set_ylabel('Frequency', fontsize=12, fontweight='bold')
        ax.set_title('Distribution of AI Detection Scores by Content Type', 
                     fontsize=14, fontweight='bold', pad=20)
        ax.legend(fontsize=11)
        ax.grid(True, alpha=0.3, axis='y')
        
        # Add statistics text
        if real_scores and fake_scores:
            stats_text = (f'Real - Mean: {np.mean(real_scores):.3f}, Std: {np.std(real_scores):.3f}\n'
                         f'Fake - Mean: {np.mean(fake_scores):.3f}, Std: {np.std(fake_scores):.3f}')
            ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, fontsize=10,
                   verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
        
        plt.tight_layout()
        plt.savefig(f'{RESULTS_DIR}/detection_scores.png', dpi=300, bbox_inches='tight')
        print("  ✓ Detection scores saved")
        plt.close()
    
    def plot_score_distribution_by_class(self):
        """Box plot of scores by true class"""
        tests = self.raw_results.get("registration_tests", [])
        
        if not tests:
            print("⚠️  No test data for score distribution")
            return
        
        real_scores = [t["tamper_score"] for t in tests 
                       if t["true_label"] == "real" and t.get("status") == 200]
        fake_scores = [t["tamper_score"] for t in tests 
                       if t["true_label"] == "fake" and t.get("status") == 200]
        
        fig, ax = plt.subplots(figsize=(10, 7))
        
        bp = ax.boxplot([real_scores, fake_scores], 
                        labels=['Real Content', 'Fake Content'],
                        patch_artist=True,
                        notch=True,
                        showmeans=True)
        
        colors = ['#2ecc71', '#e74c3c']
        for patch, color in zip(bp['boxes'], colors):
            patch.set_facecolor(color)
            patch.set_alpha(0.7)
        
        ax.set_ylabel('Detection Score', fontsize=12, fontweight='bold')
        ax.set_title('Detection Score Distribution by Content Type', 
                     fontsize=14, fontweight='bold', pad=20)
        ax.grid(True, alpha=0.3, axis='y')
        ax.axhline(y=0.5, color='black', linestyle='--', linewidth=2, alpha=0.7, label='Threshold')
        ax.legend()
        
        plt.tight_layout()
        plt.savefig(f'{RESULTS_DIR}/score_boxplot.png', dpi=300, bbox_inches='tight')
        print("  ✓ Score distribution boxplot saved")
        plt.close()
    
    def plot_processing_time(self):
        """Real processing time analysis"""
        tests = self.raw_results.get("registration_tests", [])
        
        if not tests:
            print("⚠️  No timing data")
            return
        
        valid_tests = [t for t in tests if t.get("status") == 200]
        times = [t["processing_time"] for t in valid_tests]
        sizes = [t["file_size"] / (1024*1024) for t in valid_tests]  # MB
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        
        # Time distribution
        ax1.hist(times, bins=30, color='skyblue', edgecolor='black', linewidth=1.2)
        mean_time = np.mean(times)
        median_time = np.median(times)
        ax1.axvline(x=mean_time, color='red', linestyle='--', linewidth=2,
                    label=f'Mean: {mean_time:.3f}s')
        ax1.axvline(x=median_time, color='green', linestyle='--', linewidth=2,
                    label=f'Median: {median_time:.3f}s')
        ax1.set_xlabel('Processing Time (seconds)', fontsize=12, fontweight='bold')
        ax1.set_ylabel('Frequency', fontsize=12, fontweight='bold')
        ax1.set_title('Processing Time Distribution', fontsize=13, fontweight='bold', pad=15)
        ax1.legend(fontsize=10)
        ax1.grid(True, alpha=0.3, axis='y')
        
        # Time vs file size
        ax2.scatter(sizes, times, alpha=0.5, color='purple', s=30)
        ax2.set_xlabel('File Size (MB)', fontsize=12, fontweight='bold')
        ax2.set_ylabel('Processing Time (seconds)', fontsize=12, fontweight='bold')
        ax2.set_title('Processing Time vs File Size', fontsize=13, fontweight='bold', pad=15)
        ax2.grid(True, alpha=0.3)
        
        # Add correlation if enough data
        if len(sizes) > 10:
            correlation = np.corrcoef(sizes, times)[0, 1]
            ax2.text(0.05, 0.95, f'Correlation: {correlation:.3f}', 
                    transform=ax2.transAxes, fontsize=10,
                    verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
        
        plt.tight_layout()
        plt.savefig(f'{RESULTS_DIR}/processing_time.png', dpi=300, bbox_inches='tight')
        print("  ✓ Processing time saved")
        plt.close()
    
    def plot_error_analysis(self):
        """Analyze false positives and false negatives"""
        tests = self.raw_results.get("registration_tests", [])
        
        if not tests:
            print("⚠️  No error data")
            return
        
        valid_tests = [t for t in tests if t.get("status") == 200 and t.get("predicted_label")]
        
        false_positives = []
        false_negatives = []
        
        for test in valid_tests:
            true_label = 1 if test["true_label"] == "fake" else 0
            pred_label = 1 if test.get("predicted_label") == "fake" else 0
            
            if true_label == 0 and pred_label == 1:
                false_positives.append(test)
            elif true_label == 1 and pred_label == 0:
                false_negatives.append(test)
        
        fig, ax = plt.subplots(figsize=(10, 7))
        
        categories = ['True Positives', 'True Negatives', 'False Positives', 'False Negatives']
        cm = self.metrics.get("confusion_matrix", [[0, 0], [0, 0]])
        values = [cm[1][1], cm[0][0], cm[0][1], cm[1][0]]
        colors = ['#27ae60', '#3498db', '#e67e22', '#c0392b']
        
        bars = ax.bar(categories, values, color=colors, alpha=0.8, edgecolor='black', linewidth=1.5)
        ax.set_ylabel('Count', fontsize=12, fontweight='bold')
        ax.set_title('Classification Results Breakdown', fontsize=14, fontweight='bold', pad=20)
        ax.grid(True, alpha=0.3, axis='y')
        
        # Add value labels
        for bar, val in zip(bars, values):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{val}\n({val/sum(values)*100:.1f}%)', 
                   ha='center', va='bottom', fontsize=10, fontweight='bold')
        
        plt.tight_layout()
        plt.savefig(f'{RESULTS_DIR}/error_analysis.png', dpi=300, bbox_inches='tight')
        print("  ✓ Error analysis saved")
        plt.close()
    
    def print_summary(self):
        """Print summary statistics"""
        print("\n" + "="*70)
        print("AUTHX EXPERIMENTAL RESULTS SUMMARY")
        print("="*70)
        
        if not self.metrics:
            print("⚠️  No metrics available")
            return
        
        print(f"\n📊 DATASET STATISTICS")
        print(f"  Total Samples Tested: {self.metrics['total_samples']}")
        print(f"  Successful Tests: {self.data.get('successful_tests', 'N/A')}")
        
        print(f"\n🎯 CLASSIFICATION METRICS")
        print(f"  Accuracy:  {self.metrics['accuracy']:.4f} ({self.metrics['accuracy']*100:.2f}%)")
        print(f"  Precision: {self.metrics['precision']:.4f}")
        print(f"  Recall:    {self.metrics['recall']:.4f}")
        print(f"  F1-Score:  {self.metrics['f1_score']:.4f}")
        print(f"  Specificity: {self.metrics.get('specificity', 0):.4f}")
        print(f"  Sensitivity: {self.metrics.get('sensitivity', 0):.4f}")
        
        if "roc_curve" in self.metrics:
            print(f"  AUC-ROC:   {self.metrics['roc_curve']['auc']:.4f}")
        
        print(f"\n📋 CONFUSION MATRIX")
        cm = self.metrics['confusion_matrix']
        print(f"                    Predicted Real  Predicted Fake")
        print(f"  Actual Real:      {cm[0][0]:^14d}  {cm[0][1]:^14d}")
        print(f"  Actual Fake:      {cm[1][0]:^14d}  {cm[1][1]:^14d}")
        
        # Processing stats
        tests = self.raw_results.get("registration_tests", [])
        valid_tests = [t for t in tests if t.get("status") == 200]
        
        if valid_tests:
            times = [t["processing_time"] for t in valid_tests]
            print(f"\n⏱️  PROCESSING TIME STATISTICS")
            print(f"  Mean:   {np.mean(times):.4f}s")
            print(f"  Median: {np.median(times):.4f}s")
            print(f"  Std Dev: {np.std(times):.4f}s")
            print(f"  Min:    {np.min(times):.4f}s")
            print(f"  Max:    {np.max(times):.4f}s")
        
        print("="*70 + "\n")


# ============================================================================
# MAIN USAGE
# ============================================================================
def main():
    print("""
╔══════════════════════════════════════════════════════════════╗
║          Authx Real Testing & Metrics Collection             ║
║              Updated for fake/real folder structure          ║
╚══════════════════════════════════════════════════════════════╝

Your folder structure:
  test_dataset/
  ├── fake/     (AI-generated/modified images - 1k images)
  └── real/     (Original/authentic images - 1k images)

REQUIREMENTS:
1. ✓ Test dataset is ready
2. Make sure Authx backend is running: python app.py
3. Run this script: python test_authx_real.py

""")
    
    # Check if folders exist
    fake_path = Path(TEST_DATASET_DIR) / "fake"
    real_path = Path(TEST_DATASET_DIR) / "real"
    
    if not fake_path.exists() or not real_path.exists():
        print("❌ ERROR: Required folders not found!")
        print(f"   Looking for: {fake_path} and {real_path}")
        return
    
    fake_count = len(list(fake_path.glob("*.*")))
    real_count = len(list(real_path.glob("*.*")))
    
    print(f"📊 Found {fake_count} files in fake/ and {real_count} files in real/")
    
    response = input("\nStart testing? (y/n): ").strip().lower()
    
    if response != 'y':
        print("\n❌ Testing cancelled.")
        return
    
    # Ask about sample limit
    max_samples = input(f"\nMax samples per class? (default={MAX_SAMPLES_PER_CLASS}, press Enter to use default): ").strip()
    if max_samples:
        try:
            max_samples = int(max_samples)
        except:
            max_samples = MAX_SAMPLES_PER_CLASS
    else:
        max_samples = MAX_SAMPLES_PER_CLASS
    
    print(f"\n🚀 Starting tests with up to {max_samples} samples per class...\n")
    
    # Run tests
    tester = AuthxTester()
    tester.run_batch_test(TEST_DATASET_DIR, max_samples=max_samples)
    
    # Save results
    results_file = tester.save_results()
    
    # Calculate and display metrics
    metrics = tester.calculate_metrics()
    
    if metrics:
        print("\n" + "="*70)
        print("QUICK METRICS PREVIEW")
        print("="*70)
        print(f"Accuracy: {metrics['accuracy']:.4f} ({metrics['accuracy']*100:.2f}%)")
        print(f"F1-Score: {metrics['f1_score']:.4f}")
        print(f"Precision: {metrics['precision']:.4f}")
        print(f"Recall: {metrics['recall']:.4f}")
        if "roc_curve" in metrics:
            print(f"AUC-ROC: {metrics['roc_curve']['auc']:.4f}")
        print("="*70)
    
    # Generate plots
    print("\n📊 Generating visualizations...")
    plotter = RealPlotGenerator(results_file)
    plotter.plot_all()
    plotter.print_summary()
    
    print(f"\n✅ All done! Check {RESULTS_DIR}/ for:")
    print(f"   - test_results.json (raw data)")
    print(f"   - confusion_matrix.png")
    print(f"   - roc_curve.png")
    print(f"   - detection_scores.png")
    print(f"   - score_boxplot.png")
    print(f"   - processing_time.png")
    print(f"   - error_analysis.png")
    print(f"\n📄 Use these results for your research paper!")


if __name__ == "__main__":
    main()