"""
Multi-Modal Benchmark System for Authx - FIXED VERSION
Tests video, audio, and text/document theft detection
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

# Import your modules
from ai_detector import EnhancedAITamperingDetector
from app import (
    compute_sha256, 
    compute_multi_hashes, 
    calculate_multi_similarity,
    compute_audio_fingerprint,
    compute_video_fingerprint,
    compute_text_fingerprint
)


def extract_original_name(stolen_filename: str) -> str:
    """
    FIXED: Extract original filename from theft attempt filename
    """
    base_name = Path(stolen_filename).stem
    
    # All possible modification suffixes
    suffixes = [
        '_stolen', '_bright', '_speed', '_trimmed',
        '_cropped', '_mirrored', '_resized',
        '_bw', '_compressed',
        '_faded', '_louder', '_faster', '_normalized',
        '_lowquality', '_reversed',
        '_lineends', '_spaced', '_whitespace',
        '_removed', '_shuffled', '_synonyms',
        '_half', '_lowercase', '_nopunct'
    ]
    
    original_name = base_name
    for suffix in suffixes:
        if base_name.endswith(suffix):
            original_name = base_name[:-len(suffix)]
            break
    
    return original_name


class MultiModalBenchmark:
    """
    Comprehensive benchmark for video, audio, and text content theft detection
    """
    
    def __init__(self, dataset_path: str, fast_mode: bool = False):
        self.dataset_path = Path(dataset_path)
        self.detector = EnhancedAITamperingDetector()
        self.fast_mode = fast_mode
        
        # Separate registries for each modality
        self.registered_content = {
            'video': {},
            'audio': {},
            'text': {}
        }
        
        self.results = {
            'video': defaultdict(lambda: {'detected': 0, 'total': 0}),
            'audio': defaultdict(lambda: {'detected': 0, 'total': 0}),
            'text': defaultdict(lambda: {'detected': 0, 'total': 0}),
            'processing_times': defaultdict(list)
        }
        
        if fast_mode:
            print("⚡ FAST MODE ENABLED")
    
    def run_full_benchmark(self):
        """Run complete multi-modal benchmark"""
        print("="*70)
        print("AUTHX MULTI-MODAL CONTENT THEFT DETECTION BENCHMARK")
        print("Testing: Video, Audio, Text/Documents")
        print("="*70)
        
        all_results = {}
        
        # Test each modality
        for modality in ['video', 'audio', 'text']:
            print(f"\n{'='*70}")
            print(f"TESTING {modality.upper()} CONTENT")
            print(f"{'='*70}")
            
            # Phase 1: Register originals
            print(f"\n[Phase 1] Registering Original {modality.title()} Content...")
            self.register_originals(modality)
            
            # Phase 2: Test theft detection
            print(f"\n[Phase 2] Testing {modality.title()} Theft Detection...")
            theft_results = self.test_theft_detection(modality)
            
            # Phase 3: Test false positives
            print(f"\n[Phase 3] Testing {modality.title()} False Positives...")
            fp_results = self.test_false_positives(modality)
            
            # Phase 4: Performance
            print(f"\n[Phase 4] {modality.title()} Performance Analysis...")
            perf_results = self.analyze_performance(modality)
            
            all_results[modality] = {
                'theft_detection': theft_results,
                'false_positives': fp_results,
                'performance': perf_results
            }
        
        # Generate comprehensive report
        self.generate_multimodal_report(all_results)
    
    def register_originals(self, modality: str):
        """FIXED: Register original content for a specific modality"""
        original_folder = self.dataset_path / modality / 'originals'
        
        if not original_folder.exists():
            print(f"  ⚠️  Folder not found: {original_folder}")
            print(f"     Please create and add original {modality} files")
            return
        
        extensions = self._get_extensions(modality)
        registered_count = 0
        
        print(f"  📁 Scanning: {original_folder}")
        
        for file_path in sorted(original_folder.glob('*')):
            if file_path.suffix.lower() not in extensions:
                continue
            
            try:
                with open(file_path, 'rb') as f:
                    file_bytes = f.read()
                
                # Compute fingerprints
                sha256 = compute_sha256(file_bytes)
                content_type = self._get_content_type(modality, file_path.suffix)
                hashes = compute_multi_hashes(file_bytes, content_type)
                
                # Use stem as key (filename without extension)
                original_key = file_path.stem
                
                # Store in registry
                self.registered_content[modality][original_key] = {
                    'sha256': sha256,
                    'hashes': hashes,
                    'owner': f"Creator_{original_key}",
                    'content_type': content_type,
                    'file_bytes': file_bytes
                }
                
                registered_count += 1
                
                if registered_count <= 3:  # Show first 3
                    print(f"    ✓ {original_key}")
                
            except Exception as e:
                print(f"    ✗ Error: {file_path.name} - {e}")
        
        print(f"  ✅ Registered {registered_count} {modality} items")
        if registered_count > 0:
            sample_keys = list(self.registered_content[modality].keys())[:3]
            print(f"  📋 Sample keys: {sample_keys}")
    
    def test_theft_detection(self, modality: str) -> Dict:
        """FIXED: Test theft detection for a specific modality"""
        results = {
            'exact_copies': {'detected': 0, 'total': 0, 'detection_rate': 0},
            'minor_edits': {'detected': 0, 'total': 0, 'detection_rate': 0},
            'moderate_edits': {'detected': 0, 'total': 0, 'detection_rate': 0},
            'heavy_edits': {'detected': 0, 'total': 0, 'detection_rate': 0},
            'detailed_results': []
        }
        
        modification_levels = [
            'exact_copies',
            'minor_edits',
            'moderate_edits',
            'heavy_edits'
        ]
        
        extensions = self._get_extensions(modality)
        
        for level in modification_levels:
            theft_folder = self.dataset_path / modality / 'theft_attempts' / level
            
            if not theft_folder.exists():
                print(f"  ⚠️  Skipping {level} - folder not found")
                continue
            
            theft_files = sorted([f for f in theft_folder.glob('*') 
                          if f.suffix.lower() in extensions])
            
            print(f"\n  Testing {level}: {len(theft_files)} files")
            
            for idx, stolen_file in enumerate(theft_files, 1):
                # FIXED: Extract original name properly
                original_name = extract_original_name(stolen_file.name)
                
                # Debug info for first file
                if idx == 1:
                    print(f"    [Debug] Stolen file: {stolen_file.name}")
                    print(f"    [Debug] Looking for: '{original_name}'")
                    available = list(self.registered_content[modality].keys())[:3]
                    print(f"    [Debug] Available: {available}")
                
                if original_name not in self.registered_content[modality]:
                    print(f"    [{idx}/{len(theft_files)}] ⚠️  No original for {stolen_file.name}")
                    continue
                
                try:
                    start_time = time.time()
                    detection_result = self.simulate_upload_attempt(
                        stolen_file, modality, original_name
                    )
                    processing_time = time.time() - start_time
                    
                    self.results['processing_times'][modality].append(processing_time)
                    results[level]['total'] += 1
                    
                    status_icon = "🚫" if detection_result['status'] == 'blocked' else "✅"
                    print(f"    [{idx}/{len(theft_files)}] {status_icon} "
                          f"{stolen_file.name[:40]:40} - {detection_result['status']:10} "
                          f"({processing_time*1000:6.1f}ms)")
                    
                    if detection_result['status'] == 'blocked':
                        results[level]['detected'] += 1
                        results['detailed_results'].append({
                            'modification_level': level,
                            'file': stolen_file.name,
                            'original_owner': detection_result['original_owner'],
                            'similarity': detection_result.get('similarity', 0),
                            'processing_time_ms': processing_time * 1000
                        })
                    
                except Exception as e:
                    print(f"    [{idx}/{len(theft_files)}] ❌ Error: {str(e)[:60]}")
        
        # Calculate detection rates
        for level in modification_levels:
            if results[level]['total'] > 0:
                results[level]['detection_rate'] = (
                    results[level]['detected'] / results[level]['total']
                ) * 100
                print(f"  {level}: {results[level]['detection_rate']:.1f}% "
                      f"({results[level]['detected']}/{results[level]['total']})")
        
        # Overall rate
        total_detected = sum(r['detected'] for r in results.values() 
                           if isinstance(r, dict) and 'detected' in r)
        total_attempts = sum(r['total'] for r in results.values() 
                           if isinstance(r, dict) and 'total' in r)
        
        if total_attempts > 0:
            results['overall_detection_rate'] = (total_detected / total_attempts) * 100
            print(f"\n  Overall Detection Rate: {results['overall_detection_rate']:.2f}%")
        
        return results
    
    def simulate_upload_attempt(self, file_path: Path, modality: str, original_name: str = None) -> Dict:
        """FIXED: Simulate upload attempt for any modality"""
        with open(file_path, 'rb') as f:
            file_bytes = f.read()
        
        sha256 = compute_sha256(file_bytes)
        content_type = self._get_content_type(modality, file_path.suffix)
        hashes = compute_multi_hashes(file_bytes, content_type)
        
        # Layer 1: Exact SHA256 match
        for orig_name, original_data in self.registered_content[modality].items():
            if sha256 == original_data['sha256']:
                return {
                    'status': 'blocked',
                    'reason': 'exact_match',
                    'original_owner': original_data['owner'],
                    'similarity': 100.0
                }
        
        # Layer 2: Similarity check
        best_match = None
        best_similarity = 0
        
        for orig_name, original_data in self.registered_content[modality].items():
            similarity_result = calculate_multi_similarity(
                hashes,
                original_data['hashes'],
                content_type
            )
            
            distance = similarity_result['min_distance']
            similarity_pct = max(0, (1 - distance / 64) * 100)
            
            # Get threshold
            threshold = self._get_threshold(modality, distance)
            
            if distance <= threshold and similarity_pct > best_similarity:
                best_similarity = similarity_pct
                best_match = {
                    'status': 'blocked',
                    'reason': 'similar_content',
                    'original_owner': original_data['owner'],
                    'similarity': similarity_pct,
                    'distance': distance
                }
        
        if best_match:
            return best_match
        
        return {
            'status': 'allowed',
            'reason': 'no_match',
            'original_owner': None,
            'similarity': 0.0
        }
    
    def test_false_positives(self, modality: str) -> Dict:
        """Test false positives for a specific modality"""
        results = {
            'legitimate_uploads': 0,
            'wrongly_blocked': 0,
            'false_positive_rate': 0.0,
            'examples': []
        }
        
        legitimate_folder = self.dataset_path / modality / 'legitimate_different'
        
        if not legitimate_folder.exists():
            print(f"  ⚠️  Legitimate folder not found")
            return results
        
        extensions = self._get_extensions(modality)
        
        for file_path in legitimate_folder.glob('*'):
            if file_path.suffix.lower() not in extensions:
                continue
            
            try:
                detection_result = self.simulate_upload_attempt(file_path, modality)
                results['legitimate_uploads'] += 1
                
                if detection_result['status'] == 'blocked':
                    results['wrongly_blocked'] += 1
                    results['examples'].append({
                        'file': file_path.name,
                        'similarity': detection_result.get('similarity', 0)
                    })
            
            except Exception as e:
                print(f"  Error testing {file_path.name}: {e}")
        
        if results['legitimate_uploads'] > 0:
            results['false_positive_rate'] = (
                results['wrongly_blocked'] / results['legitimate_uploads']
            ) * 100
            print(f"  False Positive Rate: {results['false_positive_rate']:.2f}% "
                  f"({results['wrongly_blocked']}/{results['legitimate_uploads']})")
        
        return results
    
    def analyze_performance(self, modality: str) -> Dict:
        """Analyze performance metrics for a modality"""
        results = {}
        
        times = self.results['processing_times'][modality]
        
        if times:
            times_ms = [t * 1000 for t in times]
            results['avg_processing_time_ms'] = np.mean(times_ms)
            results['median_processing_time_ms'] = np.median(times_ms)
            results['max_processing_time_ms'] = np.max(times_ms)
            results['min_processing_time_ms'] = np.min(times_ms)
            results['throughput_per_sec'] = 1000 / results['avg_processing_time_ms'] if results['avg_processing_time_ms'] > 0 else 0
            
            print(f"  Avg Time: {results['avg_processing_time_ms']:.2f}ms")
            print(f"  Throughput: {results['throughput_per_sec']:.2f} files/sec")
        
        results['registered_count'] = len(self.registered_content[modality])
        
        return results
    
    def generate_multimodal_report(self, all_results: Dict):
        """Generate comprehensive multi-modal report"""
        print("\n" + "="*70)
        print("MULTI-MODAL BENCHMARK REPORT")
        print("="*70)
        
        # Save JSON
        report = {
            'results': all_results,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        with open('multimodal_results.json', 'w') as f:
            json.dump(report, f, indent=2)
        print("\n✅ Saved: multimodal_results.json")
        
        # Generate visualizations
        self._generate_multimodal_charts(all_results)
        
        # Generate LaTeX tables
        self._generate_multimodal_tables(all_results)
        
        # Print summary
        self._print_multimodal_summary(all_results)
    
    def _generate_multimodal_charts(self, results: Dict):
        """Generate comparison charts across modalities"""
        
        # Chart 1: Detection rates by modality
        fig, axes = plt.subplots(1, 3, figsize=(18, 6))
        
        modalities = ['video', 'audio', 'text']
        colors = ['#e74c3c', '#3498db', '#2ecc71']
        
        for idx, (modality, color) in enumerate(zip(modalities, colors)):
            if modality not in results:
                continue
            
            theft_data = results[modality]['theft_detection']
            
            levels = []
            rates = []
            
            for level in ['exact_copies', 'minor_edits', 'moderate_edits', 'heavy_edits']:
                if theft_data[level]['total'] > 0:
                    levels.append(level.replace('_', ' ').title())
                    rates.append(theft_data[level]['detection_rate'])
            
            if levels:
                x = np.arange(len(levels))
                axes[idx].bar(x, rates, color=color, edgecolor='black', alpha=0.8)
                axes[idx].set_xlabel('Modification Level', fontweight='bold')
                axes[idx].set_ylabel('Detection Rate (%)', fontweight='bold')
                axes[idx].set_title(f'{modality.title()} Detection', fontweight='bold')
                axes[idx].set_xticks(x)
                axes[idx].set_xticklabels(levels, rotation=15, ha='right')
                axes[idx].set_ylim(0, 105)
                axes[idx].axhline(y=90, color='red', linestyle='--', alpha=0.3)
        
        plt.tight_layout()
        plt.savefig('multimodal_detection_rates.png', dpi=300, bbox_inches='tight')
        print("✅ Saved: multimodal_detection_rates.png")
        plt.close()
        
        # Chart 2: Performance comparison
        fig, ax = plt.subplots(figsize=(10, 6))
        
        modality_names = []
        avg_times = []
        throughputs = []
        
        for modality in modalities:
            if modality in results:
                perf = results[modality]['performance']
                if 'avg_processing_time_ms' in perf:
                    modality_names.append(modality.title())
                    avg_times.append(perf['avg_processing_time_ms'])
                    throughputs.append(perf['throughput_per_sec'])
        
        if modality_names:
            x = np.arange(len(modality_names))
            width = 0.35
            
            ax.bar(x - width/2, avg_times, width, label='Avg Time (ms)', 
                   color='#3498db', edgecolor='black')
            ax2 = ax.twinx()
            ax2.bar(x + width/2, throughputs, width, label='Throughput (files/sec)', 
                    color='#2ecc71', edgecolor='black')
            
            ax.set_xlabel('Modality', fontweight='bold')
            ax.set_ylabel('Processing Time (ms)', fontweight='bold', color='#3498db')
            ax2.set_ylabel('Throughput (files/sec)', fontweight='bold', color='#2ecc71')
            ax.set_title('Performance Comparison Across Modalities', fontweight='bold')
            ax.set_xticks(x)
            ax.set_xticklabels(modality_names)
            
            ax.legend(loc='upper left')
            ax2.legend(loc='upper right')
        
        plt.tight_layout()
        plt.savefig('multimodal_performance.png', dpi=300, bbox_inches='tight')
        print("✅ Saved: multimodal_performance.png")
        plt.close()
    
    def _generate_multimodal_tables(self, results: Dict):
        """Generate LaTeX tables for multi-modal results"""
        
        latex = """
\\begin{table}[h]
\\centering
\\caption{Multi-Modal Content Theft Detection Performance}
\\label{tab:multimodal_detection}
\\begin{tabular}{lcccc}
\\hline
\\textbf{Modality} & \\textbf{Overall Detection} & \\textbf{FP Rate} & \\textbf{Avg Time (ms)} & \\textbf{Throughput} \\\\
\\hline
"""
        
        for modality in ['video', 'audio', 'text']:
            if modality not in results:
                continue
            
            theft = results[modality]['theft_detection']
            fp = results[modality]['false_positives']
            perf = results[modality]['performance']
            
            overall_rate = theft.get('overall_detection_rate', 0)
            fp_rate = fp.get('false_positive_rate', 0)
            avg_time = perf.get('avg_processing_time_ms', 0)
            throughput = perf.get('throughput_per_sec', 0)
            
            latex += f"{modality.title()} & {overall_rate:.1f}\\% & {fp_rate:.1f}\\% & {avg_time:.1f} & {throughput:.1f} \\\\\n"
        
        latex += """\\hline
\\end{tabular}
\\end{table}
"""
        
        with open('table_multimodal.tex', 'w') as f:
            f.write(latex)
        print("✅ Saved: table_multimodal.tex")
    
    def _print_multimodal_summary(self, results: Dict):
        """Print summary for all modalities"""
        print("\n" + "="*70)
        print("SUMMARY - ALL MODALITIES")
        print("="*70)
        
        for modality in ['video', 'audio', 'text']:
            if modality not in results:
                continue
            
            print(f"\n📊 {modality.upper()} RESULTS:")
            
            theft = results[modality]['theft_detection']
            fp = results[modality]['false_positives']
            perf = results[modality]['performance']
            
            print(f"   • Overall Detection Rate: {theft.get('overall_detection_rate', 0):.2f}%")
            print(f"   • False Positive Rate: {fp.get('false_positive_rate', 0):.2f}%")
            print(f"   • Average Processing Time: {perf.get('avg_processing_time_ms', 0):.2f}ms")
            print(f"   • Throughput: {perf.get('throughput_per_sec', 0):.2f} files/sec")
    
    # Helper methods
    
    def _get_extensions(self, modality: str) -> List[str]:
        """Get file extensions for a modality"""
        extensions = {
            'video': ['.mp4', '.mov', '.avi', '.mkv', '.webm'],
            'audio': ['.mp3', '.wav', '.m4a', '.flac', '.ogg', '.wwav'],
            'text': ['.txt', '.pdf', '.doc', '.docx', '.md']
        }
        return extensions.get(modality, [])
    
    def _get_content_type(self, modality: str, extension: str) -> str:
        """Get MIME type for a file"""
        types = {
            'video': 'video/mp4',
            'audio': 'audio/mpeg',
            'text': 'text/plain'
        }
        
        if extension.lower() == '.pdf':
            return 'application/pdf'
        
        return types.get(modality, 'application/octet-stream')
    
    def _get_threshold(self, modality: str, distance: int) -> int:
        """FIXED: Get detection threshold for a modality"""
        thresholds = {
            'video': 25,  # Stricter for video
            'audio': 22,  # Stricter for audio
            'text': 20    # Stricter for text
        }
        return thresholds.get(modality, 25)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("="*70)
        print("AUTHX MULTI-MODAL BENCHMARK")
        print("="*70)
        print("\nUsage: python multimodal_benchmark.py <dataset_path> [--fast]")
        print("\nDataset Structure:")
        print("  dataset/")
        print("    ├── video/")
        print("    │   ├── originals/")
        print("    │   ├── theft_attempts/")
        print("    │   │   ├── exact_copies/")
        print("    │   │   ├── minor_edits/")
        print("    │   │   ├── moderate_edits/")
        print("    │   │   └── heavy_edits/")
        print("    │   └── legitimate_different/")
        print("    ├── audio/")
        print("    │   └── (same structure)")
        print("    └── text/")
        print("        └── (same structure)")
        print("\n" + "="*70)
        sys.exit(1)
    
    dataset_path = sys.argv[1]
    fast_mode = '--fast' in sys.argv
    
    benchmark = MultiModalBenchmark(dataset_path, fast_mode=fast_mode)
    benchmark.run_full_benchmark()