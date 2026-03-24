"""
[ASTRONOMY PROCESSING]: Exoplanet detection and analysis pipeline
Integrates lightkurve for Kepler data processing and BLS analysis
"""

import numpy as np
import pandas as pd
import lightkurve as lk
import matplotlib.pyplot as plt
import io
import base64
import json
import time
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import warnings

# Suppress lightkurve warnings
warnings.filterwarnings('ignore', category=UserWarning)
lk.log.setLevel('WARNING')

# Configuration
TARGETS = {
    "Kepler-8 (Hot Jupiter)": ("Kepler-8", 4),
    "Kepler-1 (TrES-2b, Hot Jupiter)": ("Kepler-1", 4),
    "Kepler-2 (HAT-P-7b, Hot Jupiter)": ("Kepler-2", 4),
    "Kepler-10": ("Kepler-10", 5),
    "Kepler-11": ("Kepler-11", 3),
}

class ExoplanetPipeline:
    """
    [ASTRONOMY PROCESSING]: End-to-end exoplanet detection pipeline
    - Fetches Kepler light curves
    - Detrends and cleans signal
    - Runs Box Least Squares (BLS) for transit detection
    - Phase-folds at orbital period
    - Returns analysis results with visualizations
    """
    
    def __init__(self):
        self.reset()
        
    def reset(self):
        """Reset all analysis data for a new target"""
        self.raw_lc = None
        self.clean_lc = None
        self.bls = None
        self.folded_lc = None
        self.target_info = None
        self.analysis_complete = False
        print("[PIPELINE] Reset - ready for new analysis")
        
    def search_targets(self) -> List[Dict]:
        """[ASTRONOMY PROCESSING]: Get list of available target systems"""
        return [
            {
                "id": kepler_id,
                "display_name": display_name,
                "quarter": quarter
            }
            for display_name, (kepler_id, quarter) in TARGETS.items()
        ]
    
    def fetch_lightcurve(self, target_name: str, max_retries: int = 3) -> Dict:
        """
        [ASTRONOMY PROCESSING]: Download Kepler light curve for target
        Returns raw flux, time, and metadata
        Includes retry logic for network/session errors
        """
        try:
            if target_name not in TARGETS:
                raise ValueError(f"Target '{target_name}' not found")
            
            kepler_id, quarter = TARGETS[target_name]
            
            # Retry loop for handling session errors
            for attempt in range(max_retries):
                try:
                    print(f"[LIGHTKURVE] Fetching {kepler_id} Q{quarter} (attempt {attempt + 1}/{max_retries})")
                    
                    # Search with explicit timeout
                    search_result = lk.search_lightcurve(
                        kepler_id,
                        author='Kepler',
                        quarter=quarter,
                        cadence='long'  # Only long cadence data
                    )
                    
                    if len(search_result) == 0:
                        raise Exception(f"No light curve found for {kepler_id} Q{quarter}")
                    
                    # Download with error handling
                    print(f"[LIGHTKURVE] Downloading {len(search_result)} file(s)...")
                    self.raw_lc = search_result.download()
                    
                    if self.raw_lc is None:
                        raise Exception("Downloaded light curve is None")
                    
                    print(f"[LIGHTKURVE] Successfully downloaded {len(self.raw_lc)} points")
                    break  # Success - exit retry loop
                    
                except Exception as e:
                    error_str = str(e).lower()
                    
                    # Check for session/connection errors
                    if 'kill state' in error_str or 'session' in error_str or 'connection' in error_str:
                        if attempt < max_retries - 1:
                            print(f"[LIGHTKURVE WARNING] Session error, retrying in 3 seconds...")
                            time.sleep(3)  # Wait before retry
                            continue
                        else:
                            raise Exception(f"Archive connection failed after {max_retries} attempts. The Kepler archive may be temporarily unavailable. Please try again in a few moments.")
                    
                    # Other errors - don't retry
                    raise
            
            # Extract data
            time = self.raw_lc.time.jd
            flux = self.raw_lc.flux.value
            flux_err = self.raw_lc.flux_err.value if hasattr(self.raw_lc, 'flux_err') else np.ones_like(flux) * 0.001
            
            # Handle masked arrays
            if hasattr(flux, 'filled'):
                flux = flux.filled(np.nan)
            if hasattr(flux_err, 'filled'):
                flux_err = flux_err.filled(np.nan)
            
            self.target_info = {
                "target_name": target_name,
                "kepler_id": kepler_id,
                "quarter": quarter,
                "downloaded_at": datetime.utcnow().isoformat()
            }
            
            return {
                "status": "success",
                "time": time.tolist(),
                "flux": flux.tolist(),
                "flux_err": flux_err.tolist(),
                "n_points": len(time),
                "target": self.target_info
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def detrend_signal(self) -> Dict:
        """
        [ASTRONOMY PROCESSING]: Flatten and denoise light curve
        - Uses Savitzky-Golay filter (window_length=401)
        - Removes NaN values
        - Removes outliers
        """
        try:
            if self.raw_lc is None:
                raise ValueError("No light curve loaded. Call fetch_lightcurve first.")
            
            print(f"[DETREND] Detrending {len(self.raw_lc)} raw points...")
            
            # Detrend with error handling
            self.clean_lc = self.raw_lc.flatten(window_length=401).remove_nans().remove_outliers()
            
            if self.clean_lc is None or len(self.clean_lc) == 0:
                raise ValueError("Detrending resulted in empty light curve")
            
            time = self.clean_lc.time.jd
            flux = self.clean_lc.flux.value
            
            # Handle masked arrays
            if hasattr(flux, 'filled'):
                flux = flux.filled(np.nan)
            
            print(f"[DETREND] After detrending: {len(self.clean_lc)} points remain")
            
            return {
                "status": "success",
                "time": time.tolist(),
                "flux": flux.tolist(),
                "n_points": len(time),
                "message": "Detrended using Savitzky-Golay filter (window=401)"
            }
        except Exception as e:
            print(f"[DETREND ERROR] {str(e)}")
            return {"status": "error", "message": f"Detrending failed: {str(e)}"}
    
    def run_bls(self, period_range: Tuple[float, float] = (0.5, 10)) -> Dict:
        """
        [ASTRONOMY PROCESSING]: Box Least Squares transit detection
        Searches for periodic transits in specified period range
        Default: 0.5 to 10 days (suitable for hot Jupiters)
        """
        try:
            if self.clean_lc is None:
                raise ValueError("No clean light curve. Call detrend_signal first.")
            
            # Check for insufficient data
            if len(self.clean_lc) < 100:
                raise ValueError(f"Insufficient data points ({len(self.clean_lc)} < 100)")
            
            print(f"[BLS] Running Box Least Squares analysis on {len(self.clean_lc)} points...")
            
            # Run BLS with progress
            period_grid = np.linspace(period_range[0], period_range[1], 1000)
            self.bls = self.clean_lc.to_periodogram(method='bls', period=period_grid)
            
            if self.bls is None:
                raise ValueError("BLS periodogram computation failed")
            
            # Extract results
            planet_period = self.bls.period_at_max_power
            planet_t0 = self.bls.transit_time_at_max_power
            transit_depth = self.bls.depth_at_max_power
            transit_duration = self.bls.duration_at_max_power
            
            period_values = self.bls.period.value
            power_values = self.bls.power.value
            
            print(f"[BLS] Peak found at {planet_period.value:.4f} days with power {power_values.max():.4f}")
            
            return {
                "status": "success",
                "period_values": period_values.tolist(),
                "power_values": power_values.tolist(),
                "detected_period": float(planet_period.value),
                "detected_t0": float(planet_t0.jd),
                "transit_depth_ppm": float(transit_depth.value * 1e6),
                "transit_duration_hours": float(transit_duration.value * 24),
                "message": f"Transit detected at {planet_period.value:.2f} days"
            }
        except Exception as e:
            print(f"[BLS ERROR] {str(e)}")
            return {"status": "error", "message": f"BLS analysis failed: {str(e)}"}
    
    def phase_fold(self) -> Dict:
        """
        [ASTRONOMY PROCESSING]: Phase-fold light curve at orbital period
        Shows phase-folded transit for visual inspection
        """
        try:
            if self.bls is None:
                raise ValueError("No BLS results. Call run_bls first.")
            
            planet_period = self.bls.period_at_max_power
            planet_t0 = self.bls.transit_time_at_max_power
            
            # Phase fold
            self.folded_lc = self.clean_lc.fold(period=planet_period, epoch_time=planet_t0)
            
            phase = self.folded_lc.time.value
            flux = self.folded_lc.flux.value
            
            # Handle masked arrays
            if hasattr(flux, 'filled'):
                flux = flux.filled(np.nan)
            
            # Sort by phase for proper visualization
            sort_idx = np.argsort(phase)
            phase_sorted = phase[sort_idx]
            flux_sorted = flux[sort_idx]
            
            return {
                "status": "success",
                "phase": phase_sorted.tolist(),
                "flux": flux_sorted.tolist(),
                "n_transits": int(np.ceil((self.clean_lc.time.jd.max() - self.clean_lc.time.jd.min()) / 
                                         float(self.bls.period_at_max_power.value))),
                "message": f"Phase-folded at {float(self.bls.period_at_max_power.value):.2f} days"
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def get_summary_statistics(self) -> Dict:
        """[ASTRONOMY PROCESSING]: Calculate summary statistics for analysis"""
        try:
            if self.bls is None or self.folded_lc is None:
                raise ValueError("Analysis not complete. Run full pipeline first.")
            
            # Calculate SNR (Signal-to-Noise Ratio)
            transit_depth = self.bls.depth_at_max_power.value
            flux_std = np.nanstd(self.clean_lc.flux.value)
            snr = transit_depth / (flux_std / np.sqrt(len(self.clean_lc)))
            
            # Transit statistics
            planet_period = self.bls.period_at_max_power
            transit_duration = self.bls.duration_at_max_power
            
            return {
                "status": "success",
                "target_name": self.target_info.get("target_name") if self.target_info else "Unknown",
                "orbital_period_days": float(planet_period.value),
                "transit_duration_hours": float(transit_duration.value * 24),
                "transit_depth_ppm": float(self.bls.depth_at_max_power.value * 1e6),
                "snr": float(snr),
                "data_points": len(self.clean_lc),
                "time_span_days": float(self.clean_lc.time.jd.max() - self.clean_lc.time.jd.min())
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def generate_plot(self, plot_type: str) -> str:
        """
        [ASTRONOMY PROCESSING]: Generate matplotlib plot and return as base64
        Supported types: raw_lc, detrended_lc, bls_periodogram, folded_lc
        """
        try:
            fig, ax = plt.subplots(figsize=(10, 5))
            
            if plot_type == "raw_lc":
                if self.raw_lc is None:
                    raise ValueError("No raw light curve")
                self.raw_lc.plot(ax=ax, color='gray')
                ax.set_title("Raw Time-Series Flux")
                ax.set_ylabel("Flux (e⁻/s)")
                ax.set_xlabel("Time (JD)")
            
            elif plot_type == "detrended_lc":
                if self.clean_lc is None:
                    raise ValueError("No detrended light curve")
                self.clean_lc.plot(ax=ax, color='blue')
                ax.set_title("Detrended Signal")
                ax.set_ylabel("Normalized Flux")
                ax.set_xlabel("Time (JD)")
            
            elif plot_type == "bls_periodogram":
                if self.bls is None:
                    raise ValueError("No BLS results")
                self.bls.plot(ax=ax, color='black')
                ax.set_title("BLS Periodogram (Transit Detection)")
                ax.set_ylabel("BLS Power")
                ax.set_xlabel("Period (days)")
            
            elif plot_type == "folded_lc":
                if self.folded_lc is None:
                    raise ValueError("No phase-folded light curve")
                self.folded_lc.scatter(ax=ax, color='black', s=10)
                ax.set_xlim(-0.2, 0.2)
                ax.set_title("Phase-Folded Transit")
                ax.set_ylabel("Normalized Flux")
                ax.set_xlabel("Phase")
            
            else:
                raise ValueError(f"Unknown plot type: {plot_type}")
            
            plt.tight_layout()
            
            # Convert to base64
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
            buffer.seek(0)
            img_base64 = base64.b64encode(buffer.read()).decode()
            plt.close(fig)
            
            return img_base64
        except Exception as e:
            return f"error:{str(e)}"

# Global pipeline instance
pipeline = ExoplanetPipeline()
