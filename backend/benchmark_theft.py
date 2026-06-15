"""
Benchmark Testing for Authx Content Theft Detection System
Tests the system's ability to detect stolen content with various modifications
"""

import os
import json
import time
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple
import matplotlib.pyplot as plt
import seaborn as sns
from collections import defaultdict
import pandas as pd

# Import your modules
from ai_detector import EnhancedAITamperingDetector
from app import compute_sha256, compute_multi_hashes, calculate_multi_similarity

class TheftDetectionBenchmark:
    """
    Tests Authx's ability to detect stolen/modified content
    Simulates: Original Upload → Theft Attempts → Detection
    """
    
    def __init__(self, dataset_path: str, fast_mode: bool = False):
        self.dataset_path = Path(dataset_path)
        self.detector = EnhancedAITamperingDetector()
        self.fast_mode = fast_mode  # Skip some AI detection for speed
        
        # Simulated database of registered content
        self.registered_content = {}
        
        # Cache for AI detection results (to avoid reprocessing)
        self.ai_detection_cache = {}
        
        self.results = {
            'theft_detection_rate': [],
            'false_positives': [],
            'processing_times': [],
            'modification_levels': defaultdict(lambda: {'detected': 0, 'total': 0})
        }
        
        if fast_mode:
            print("⚡ FAST MODE ENABLED - AI detection limited for speed")
    
    def run_full_benchmark(self):
        """Run complete theft detection benchmark"""
        print("="*70)
        print("AUTHX CONTENT THEFT DETECTION BENCHMARK")
        print("Scenario: Detect stolen content with various modifications")
        print("="*70)
        
        # Phase 1: Register original content
        print("\n[Phase 1] Registering Original Content...")
        self.register_originals()
        
        # Phase 2: Test theft detection with modifications
        print("\n[Phase 2] Testing Theft Detection...")
        theft_results = self.test_theft_detection()
        
        # Phase 3: Test legitimate uploads (should NOT be blocked)
        print("\n[Phase 3] Testing Legitimate Uploads (False Positive Check)...")
        false_positive_results = self.test_false_positives()
        
        # Phase 4: Edge cases
        print("\n[Phase 4] Testing Edge Cases...")
        edge_case_results = self.test_edge_cases()
        
        # Phase 5: Performance metrics
        print("\n[Phase 5] Performance Analysis...")
        performance_results = self.analyze_performance()
        
        # Generate comprehensive report
        self.generate_report({
            'theft_detection': theft_results,
            'false_positives': false_positive_results,
            'edge_cases': edge_case_results,
            'performance': performance_results
        })
    
    def register_originals(self):
        """
        Phase 1: Register original content (simulate database)
        """
        original_folder = self.dataset_path / 'originals'
        
        if not original_folder.exists():
            print(f"⚠️  Please create folder: {original_folder}")
            print("   Add 30-50 original images that 'creators' uploaded")
            return
        
        registered_count = 0
        
        for img_file in original_folder.glob('*'):
            if img_file.suffix.lower() not in ['.jpg', '.jpeg', '.png', '.webp']:
                continue
            
            try:
                with open(img_file, 'rb') as f:
                    file_bytes = f.read()
                
                # Compute fingerprints
                sha256 = compute_sha256(file_bytes)
                hashes = compute_multi_hashes(file_bytes, 'image/jpeg')
                
                # Store in "database"
                self.registered_content[img_file.stem] = {
                    'sha256': sha256,
                    'hashes': hashes,
                    'owner': f"Creator_{img_file.stem}",
                    'content_type': 'image/jpeg',
                    'file_bytes': file_bytes  # For similarity testing
                }
                
                registered_count += 1
                
            except Exception as e:
                print(f"Error registering {img_file}: {e}")
        
        print(f"✅ Registered {registered_count} original content items")
    
    def test_theft_detection(self) -> Dict:
        """
        Phase 2: Test detection of stolen content with modifications
        
        Theft scenarios:
        1. Exact copy (SHA-256 match)
        2. Minor edits (crop, brightness) - should detect
        3. Moderate edits (filters, resize) - should detect
        4. Heavy AI modifications (style transfer, AI upscale) - should detect
        5. Extreme modifications - may miss (acceptable)
        """
        
        results = {
            'exact_copies': {'detected': 0, 'total': 0, 'detection_rate': 0},
            'minor_edits': {'detected': 0, 'total': 0, 'detection_rate': 0},
            'moderate_edits': {'detected': 0, 'total': 0, 'detection_rate': 0},
            'heavy_ai_edits': {'detected': 0, 'total': 0, 'detection_rate': 0},
            'extreme_edits': {'detected': 0, 'total': 0, 'detection_rate': 0},
            'detailed_results': []
        }
        
        modification_levels = [
            ('exact_copies', 'exact_copies'),
            ('minor_edits', 'minor_edits'),
            ('moderate_edits', 'moderate_edits'),
            ('heavy_ai_edits', 'heavy_ai_edits'),
            ('extreme_edits', 'extreme_edits')
        ]
        
        for level_name, folder_name in modification_levels:
            theft_folder = self.dataset_path / 'theft_attempts' / folder_name
            
            if not theft_folder.exists():
                print(f"  ⚠️  Skipping {level_name} - folder not found")
                continue
            
            # Count total files first
            theft_files = [f for f in theft_folder.glob('*') 
                          if f.suffix.lower() in ['.jpg', '.jpeg', '.png', '.webp']]
            
            print(f"\n  Testing {level_name}: {len(theft_files)} files")
            
            for idx, stolen_file in enumerate(theft_files, 1):
                # Extract original name (format: original_name_modified.jpg)
                original_name = stolen_file.stem.split('_')[0]
                
                if original_name not in self.registered_content:
                    print(f"    [{idx}/{len(theft_files)}] ⚠️  No original found for {stolen_file.name}")
                    continue
                
                try:
                    # Simulate upload attempt by thief
                    start_time = time.time()
                    detection_result = self.simulate_upload_attempt(stolen_file)
                    processing_time = time.time() - start_time
                    
                    self.results['processing_times'].append(processing_time)
                    
                    results[level_name]['total'] += 1
                    
                    # Check if theft was detected
                    status_icon = "🚫" if detection_result['status'] == 'blocked' else "✅"
                    print(f"    [{idx}/{len(theft_files)}] {status_icon} {stolen_file.name[:40]:40} - "
                          f"{detection_result['status']:10} ({processing_time*1000:6.1f}ms)")
                    
                    if detection_result['status'] == 'blocked':
                        results[level_name]['detected'] += 1
                        
                        # Record details
                        results['detailed_results'].append({
                            'modification_level': level_name,
                            'file': stolen_file.name,
                            'original_owner': detection_result['original_owner'],
                            'similarity': detection_result['similarity'],
                            'tamper_score': detection_result['tamper_score'],
                            'processing_time_ms': processing_time * 1000
                        })
                    
                except Exception as e:
                    print(f"    [{idx}/{len(theft_files)}] ❌ Error testing {stolen_file.name}: {str(e)[:60]}")
        
        # Calculate detection rates
        for level in ['exact_copies', 'minor_edits', 'moderate_edits', 'heavy_ai_edits', 'extreme_edits']:
            if results[level]['total'] > 0:
                results[level]['detection_rate'] = (
                    results[level]['detected'] / results[level]['total']
                ) * 100
                
                print(f"  {level}: {results[level]['detection_rate']:.1f}% "
                      f"({results[level]['detected']}/{results[level]['total']})")
        
        # Overall detection rate
        total_detected = sum(r['detected'] for r in results.values() if isinstance(r, dict) and 'detected' in r)
        total_attempts = sum(r['total'] for r in results.values() if isinstance(r, dict) and 'total' in r)
        
        if total_attempts > 0:
            results['overall_detection_rate'] = (total_detected / total_attempts) * 100
            print(f"\n  Overall Theft Detection Rate: {results['overall_detection_rate']:.2f}%")
        
        return results
    
    def simulate_upload_attempt(self, file_path: Path) -> Dict:
        """
        Simulate what happens when someone tries to upload stolen content
        Returns: detection result
        """
        with open(file_path, 'rb') as f:
            file_bytes = f.read()
        
        sha256 = compute_sha256(file_bytes)
        hashes = compute_multi_hashes(file_bytes, 'image/jpeg')
        
        # Layer 1: Check exact SHA-256 match (fastest check)
        for original_name, original_data in self.registered_content.items():
            if sha256 == original_data['sha256']:
                return {
                    'status': 'blocked',
                    'reason': 'exact_match',
                    'original_owner': original_data['owner'],
                    'similarity': 100.0,
                    'tamper_score': 0.0
                }
        
        # Layer 2: Check similarity + tampering
        best_match = None
        best_similarity = 0
        
        for original_name, original_data in self.registered_content.items():
            similarity_result = calculate_multi_similarity(
                hashes, 
                original_data['hashes'], 
                'image/jpeg'
            )
            
            distance = similarity_result['min_distance']
            similarity_pct = max(0, (1 - distance / 64) * 100)
            
            # Run AI tampering detection (with caching)
            if self.fast_mode and distance > 40:
                # Skip AI detection if similarity is very low (optimization)
                tamper_score = 0.0
            else:
                # Use cache if available
                if sha256 in self.ai_detection_cache:
                    tampering_result = self.ai_detection_cache[sha256]
                else:
                    tampering_result = self.detector.analyze(file_bytes, 'image/jpeg')
                    self.ai_detection_cache[sha256] = tampering_result
                
                tamper_score = tampering_result.get('tamper_probability', 0)
            
            # Adaptive threshold (same as your main.py logic)
            if tamper_score > 0.3:  # AI-modified
                threshold = 35
            else:
                threshold = 18
            
            if distance <= threshold and similarity_pct > best_similarity:
                best_similarity = similarity_pct
                best_match = {
                    'status': 'blocked',
                    'reason': 'similar_content_with_modifications',
                    'original_owner': original_data['owner'],
                    'similarity': similarity_pct,
                    'hash_distance': distance,
                    'tamper_score': tamper_score,
                    'threshold_used': threshold
                }
        
        if best_match:
            return best_match
        
        # Not detected as theft
        return {
            'status': 'allowed',
            'reason': 'no_match_found',
            'original_owner': None,
            'similarity': 0.0,
            'tamper_score': 0.0
        }
    
    def test_false_positives(self) -> Dict:
        """
        Phase 3: Test legitimate uploads that should NOT be blocked
        (Different content from different creators)
        """
        results = {
            'legitimate_uploads': 0,
            'wrongly_blocked': 0,
            'false_positive_rate': 0.0,
            'examples': []
        }
        
        legitimate_folder = self.dataset_path / 'legitimate_different_content'
        
        if not legitimate_folder.exists():
            print("  ⚠️  Legitimate content folder not found")
            return results
        
        for img_file in legitimate_folder.glob('*'):
            if img_file.suffix.lower() not in ['.jpg', '.jpeg', '.png', '.webp']:
                continue
            
            try:
                detection_result = self.simulate_upload_attempt(img_file)
                
                results['legitimate_uploads'] += 1
                
                if detection_result['status'] == 'blocked':
                    results['wrongly_blocked'] += 1
                    results['examples'].append({
                        'file': img_file.name,
                        'blocked_reason': detection_result['reason'],
                        'similarity': detection_result['similarity']
                    })
            
            except Exception as e:
                print(f"  Error testing {img_file}: {e}")
        
        if results['legitimate_uploads'] > 0:
            results['false_positive_rate'] = (
                results['wrongly_blocked'] / results['legitimate_uploads']
            ) * 100
            
            print(f"  False Positive Rate: {results['false_positive_rate']:.2f}% "
                  f"({results['wrongly_blocked']}/{results['legitimate_uploads']})")
        
        return results
    
    def test_edge_cases(self) -> Dict:
        """
        Phase 4: Test edge cases
        """
        results = {
            'collage_detection': {'tested': 0, 'detected': 0},
            'partial_crop': {'tested': 0, 'detected': 0},
            'watermark_removal': {'tested': 0, 'detected': 0}
        }
        
        edge_cases = [
            ('collage_detection', 'collages'),
            ('partial_crop', 'partial_crops'),
            ('watermark_removal', 'watermark_removed')
        ]
        
        for case_name, folder_name in edge_cases:
            edge_folder = self.dataset_path / 'edge_cases' / folder_name
            
            if not edge_folder.exists():
                continue
            
            for img_file in edge_folder.glob('*'):
                if img_file.suffix.lower() not in ['.jpg', '.jpeg', '.png', '.webp']:
                    continue
                
                try:
                    detection_result = self.simulate_upload_attempt(img_file)
                    
                    results[case_name]['tested'] += 1
                    
                    if detection_result['status'] == 'blocked':
                        results[case_name]['detected'] += 1
                
                except Exception as e:
                    continue
        
        # Print results
        for case_name in ['collage_detection', 'partial_crop', 'watermark_removal']:
            if results[case_name]['tested'] > 0:
                rate = (results[case_name]['detected'] / results[case_name]['tested']) * 100
                print(f"  {case_name}: {rate:.1f}% "
                      f"({results[case_name]['detected']}/{results[case_name]['tested']})")
        
        return results
    
    def analyze_performance(self) -> Dict:
        """
        Phase 5: Performance metrics
        """
        results = {}
        
        if self.results['processing_times']:
            times_ms = [t * 1000 for t in self.results['processing_times']]
            
            results['avg_processing_time_ms'] = np.mean(times_ms)
            results['max_processing_time_ms'] = np.max(times_ms)
            results['min_processing_time_ms'] = np.min(times_ms)
            results['std_processing_time_ms'] = np.std(times_ms)
            results['throughput_per_sec'] = 1000 / results['avg_processing_time_ms']
            
            print(f"  Average Processing Time: {results['avg_processing_time_ms']:.2f}ms")
            print(f"  Throughput: {results['throughput_per_sec']:.2f} uploads/second")
            print(f"  Min/Max: {results['min_processing_time_ms']:.2f}ms / "
                  f"{results['max_processing_time_ms']:.2f}ms")
        
        # Database size simulation
        results['registered_content_count'] = len(self.registered_content)
        
        return results
    
    def generate_report(self, all_results: Dict):
        """
        Generate comprehensive benchmark report with visualizations
        """
        print("\n" + "="*70)
        print("BENCHMARK REPORT - CONTENT THEFT DETECTION")
        print("="*70)
        
        # Save JSON report
        report = {
            'dataset_info': {
                'originals_registered': len(self.registered_content),
                'theft_attempts_tested': sum(
                    r['total'] for r in all_results['theft_detection'].values() 
                    if isinstance(r, dict) and 'total' in r
                )
            },
            'results': all_results,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        with open('theft_detection_results.json', 'w') as f:
            json.dump(report, f, indent=2)
        print("\n✅ Full report saved to: theft_detection_results.json")
        
        # Generate visualizations
        self._generate_charts(all_results)
        
        # Generate LaTeX tables
        self._generate_latex_tables(all_results)
        
        # Generate summary statistics
        self._print_summary(all_results)
    
    def _generate_charts(self, results: Dict):
        """Generate visualization charts for paper"""
        
        # Chart 1: Detection Rate by Modification Level
        self._plot_detection_rates(results['theft_detection'])
        
        # Chart 2: Processing Time Distribution
        self._plot_processing_times()
        
        # Chart 3: System Performance Overview
        self._plot_performance_summary(results)
    
    def _plot_detection_rates(self, theft_results: Dict):
        """Bar chart of detection rates"""
        plt.figure(figsize=(12, 6))
        
        levels = []
        rates = []
        counts = []
        
        for level in ['exact_copies', 'minor_edits', 'moderate_edits', 
                      'heavy_ai_edits', 'extreme_edits']:
            if theft_results[level]['total'] > 0:
                levels.append(level.replace('_', ' ').title())
                rates.append(theft_results[level]['detection_rate'])
                counts.append(f"{theft_results[level]['detected']}/{theft_results[level]['total']}")
        
        x = np.arange(len(levels))
        bars = plt.bar(x, rates, color=['#2ecc71', '#27ae60', '#f39c12', '#e67e22', '#e74c3c'], 
                       edgecolor='black', alpha=0.8)
        
        # Add count labels on bars
        for i, (bar, count) in enumerate(zip(bars, counts)):
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2., height + 2,
                    count, ha='center', va='bottom', fontsize=10)
        
        plt.xlabel('Modification Level', fontsize=12, fontweight='bold')
        plt.ylabel('Detection Rate (%)', fontsize=12, fontweight='bold')
        plt.title('Theft Detection Rate by Modification Level', fontsize=14, fontweight='bold')
        plt.xticks(x, levels, rotation=15, ha='right')
        plt.ylim(0, 105)
        plt.axhline(y=90, color='r', linestyle='--', alpha=0.5, label='90% Target')
        plt.legend()
        plt.tight_layout()
        plt.savefig('detection_rates.png', dpi=300, bbox_inches='tight')
        print("✅ Saved: detection_rates.png")
        plt.close()
    
    def _plot_processing_times(self):
        """Histogram of processing times"""
        plt.figure(figsize=(10, 6))
        
        times_ms = [t * 1000 for t in self.results['processing_times']]
        
        plt.hist(times_ms, bins=30, edgecolor='black', alpha=0.7, color='#3498db')
        plt.axvline(np.mean(times_ms), color='red', linestyle='--', linewidth=2,
                   label=f'Mean: {np.mean(times_ms):.2f}ms')
        plt.axvline(np.median(times_ms), color='green', linestyle='--', linewidth=2,
                   label=f'Median: {np.median(times_ms):.2f}ms')
        
        plt.xlabel('Processing Time (ms)', fontsize=12, fontweight='bold')
        plt.ylabel('Frequency', fontsize=12, fontweight='bold')
        plt.title('Upload Processing Time Distribution', fontsize=14, fontweight='bold')
        plt.legend()
        plt.grid(axis='y', alpha=0.3)
        plt.tight_layout()
        plt.savefig('processing_times.png', dpi=300, bbox_inches='tight')
        print("✅ Saved: processing_times.png")
        plt.close()
    
    def _plot_performance_summary(self, results: Dict):
        """Summary metrics visualization"""
        fig, axes = plt.subplots(1, 3, figsize=(15, 5))
        
        theft_data = results['theft_detection']
        fp_data = results['false_positives']
        perf_data = results['performance']
        
        # Plot 1: Overall Detection Rate
        overall_rate = theft_data.get('overall_detection_rate', 0)
        axes[0].bar(['Detection\nRate'], [overall_rate], color='#2ecc71', edgecolor='black')
        axes[0].set_ylim(0, 100)
        axes[0].set_ylabel('Percentage (%)', fontweight='bold')
        axes[0].set_title('Overall Theft\nDetection Rate', fontweight='bold')
        axes[0].text(0, overall_rate + 3, f'{overall_rate:.1f}%', 
                    ha='center', fontsize=14, fontweight='bold')
        
        # Plot 2: False Positive Rate
        fp_rate = fp_data.get('false_positive_rate', 0)
        axes[1].bar(['False Positive\nRate'], [fp_rate], color='#e74c3c', edgecolor='black')
        axes[1].set_ylim(0, 20)
        axes[1].set_ylabel('Percentage (%)', fontweight='bold')
        axes[1].set_title('False Positive Rate\n(Lower is Better)', fontweight='bold')
        axes[1].text(0, fp_rate + 0.5, f'{fp_rate:.2f}%', 
                    ha='center', fontsize=14, fontweight='bold')
        
        # Plot 3: Processing Speed
        throughput = perf_data.get('throughput_per_sec', 0)
        axes[2].bar(['Throughput'], [throughput], color='#3498db', edgecolor='black')
        axes[2].set_ylabel('Uploads/Second', fontweight='bold')
        axes[2].set_title('System Throughput', fontweight='bold')
        axes[2].text(0, throughput + 0.5, f'{throughput:.1f}', 
                    ha='center', fontsize=14, fontweight='bold')
        
        plt.tight_layout()
        plt.savefig('performance_summary.png', dpi=300, bbox_inches='tight')
        print("✅ Saved: performance_summary.png")
        plt.close()
    
    def _generate_latex_tables(self, results: Dict):
        """Generate LaTeX tables for paper"""
        
        # Table 1: Detection Performance
        theft_data = results['theft_detection']
        
        latex_table1 = """
\\begin{table}[h]
\\centering
\\caption{Content Theft Detection Performance}
\\label{tab:theft_detection}
\\begin{tabular}{lccc}
\\hline
\\textbf{Modification Level} & \\textbf{Tested} & \\textbf{Detected} & \\textbf{Detection Rate} \\\\
\\hline
"""
        
        for level in ['exact_copies', 'minor_edits', 'moderate_edits', 'heavy_ai_edits', 'extreme_edits']:
            if theft_data[level]['total'] > 0:
                level_name = level.replace('_', ' ').title()
                latex_table1 += f"{level_name} & {theft_data[level]['total']} & {theft_data[level]['detected']} & {theft_data[level]['detection_rate']:.1f}\\% \\\\\n"
        
        overall_rate = theft_data.get('overall_detection_rate', 0)
        latex_table1 += f"\\hline\n\\textbf{{Overall}} & - & - & \\textbf{{{overall_rate:.1f}\\%}} \\\\\n"
        latex_table1 += """\\hline
\\end{tabular}
\\end{table}
"""
        
        with open('table_detection_performance.tex', 'w') as f:
            f.write(latex_table1)
        print("✅ Saved: table_detection_performance.tex")
        
        # Table 2: System Performance
        perf_data = results['performance']
        fp_data = results['false_positives']
        
        latex_table2 = """
\\begin{table}[h]
\\centering
\\caption{System Performance Metrics}
\\label{tab:performance}
\\begin{tabular}{lc}
\\hline
\\textbf{Metric} & \\textbf{Value} \\\\
\\hline
"""
        latex_table2 += f"Average Processing Time & {perf_data.get('avg_processing_time_ms', 0):.2f} ms \\\\\n"
        latex_table2 += f"Throughput & {perf_data.get('throughput_per_sec', 0):.2f} uploads/sec \\\\\n"
        latex_table2 += f"False Positive Rate & {fp_data.get('false_positive_rate', 0):.2f}\\% \\\\\n"
        latex_table2 += f"Registered Content Items & {perf_data.get('registered_content_count', 0)} \\\\\n"
        latex_table2 += """\\hline
\\end{tabular}
\\end{table}
"""
        
        with open('table_performance.tex', 'w') as f:
            f.write(latex_table2)
        print("✅ Saved: table_performance.tex")
    
    def _print_summary(self, results: Dict):
        """Print summary statistics"""
        print("\n" + "="*70)
        print("SUMMARY STATISTICS FOR PAPER")
        print("="*70)
        
        theft_data = results['theft_detection']
        fp_data = results['false_positives']
        perf_data = results['performance']
        
        print(f"\n📊 Key Findings:")
        print(f"   • Overall Theft Detection Rate: {theft_data.get('overall_detection_rate', 0):.2f}%")
        print(f"   • False Positive Rate: {fp_data.get('false_positive_rate', 0):.2f}%")
        print(f"   • Average Processing Time: {perf_data.get('avg_processing_time_ms', 0):.2f}ms")
        print(f"   • System Throughput: {perf_data.get('throughput_per_sec', 0):.2f} uploads/sec")
        
        print(f"\n📈 Detection by Modification Level:")
        for level in ['exact_copies', 'minor_edits', 'moderate_edits', 'heavy_ai_edits']:
            if theft_data[level]['total'] > 0:
                print(f"   • {level.replace('_', ' ').title()}: {theft_data[level]['detection_rate']:.1f}%")


# Example usage
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("="*70)
        print("AUTHX THEFT DETECTION BENCHMARK")
        print("="*70)
        print("\nUsage: python benchmark_theft.py <dataset_path> [--fast]")
        print("\nOptions:")
        print("  --fast    Enable fast mode (skips some AI detection for speed)")
        print("\nDataset Structure Required:")
        print("  dataset/")
        print("    ├── originals/              # Original content by creators")
        print("    ├── theft_attempts/")
        print("    │   ├── exact_copies/       # Exact duplicates")
        print("    │   ├── minor_edits/        # Slight modifications")
        print("    │   ├── moderate_edits/     # Filters, crops, etc.")
        print("    │   ├── heavy_ai_edits/     # AI upscaling, style transfer")
        print("    │   └── extreme_edits/      # Heavy modifications")
        print("    ├── legitimate_different_content/  # Unrelated content")
        print("    └── edge_cases/")
        print("        ├── collages/           # Images containing originals")
        print("        ├── partial_crops/      # Cropped sections")
        print("        └── watermark_removed/  # Watermark removal attempts")
        print("\nExample:")
        print("  python benchmark_theft.py benchmark_dataset")
        print("  python benchmark_theft.py benchmark_dataset --fast")
        print("\n" + "="*70)
        sys.exit(1)
    
    dataset_path = sys.argv[1]
    fast_mode = '--fast' in sys.argv
    
    benchmark = TheftDetectionBenchmark(dataset_path, fast_mode=fast_mode)
    benchmark.run_full_benchmark()