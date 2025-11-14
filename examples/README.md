# Examples for Map to GeoJSON Converter

This folder contains sample inputs and outputs to demonstrate what the tool can do.

---

## 📊 What This Tool Does

The Map to GeoJSON Converter takes map images like this:

### Input: Map Image with Regions
![Input Map](italy_input.png)

And converts them to GeoJSON format, extracting polygons for each region:

### Output: Extracted Regions as GeoJSON
![Output GeoJSON](italy_output.png)

The tool automatically:
- Detects colored regions in the map
- Extracts boundaries as polygons
- Identifies centroids for each region
- Exports as standard GeoJSON format

---

## Sample Files
- `italy_input.png`: Sample map image of Italy with regions (input example).
- `italy_output.png`: Visualization showing detected regions with labels (output example).
- `sample_output.geojson`: Expected GeoJSON output from the sample image.
- `sample_svg.svg`: An SVG map file (use for SVG-to-GeoJSON conversion).

## How to Use
1. Place your map image in this folder (or any location).
2. Run the conversion script:
   ```bash
   python "src/tests/test with ai/image_to_geojson_auto.py"
   ```
3. Enter the path to your image when prompted.
4. Choose calibration method (Italy preset recommended for Italian maps).
5. Check outputs:
   - `*_segmented.png`: Color segmentation visualization
   - `*_regions.png`: Detected polygons with centroids
   - `*.geojson`: GeoJSON file ready to use

6. Visualize the GeoJSON at https://geojson.io

---

## Expected Results

The converter will:
- Identify distinct regions based on colors
- Filter out water bodies and background
- Generate clean polygon boundaries
- Assign properties (id, color, area) to each region

Perfect for students who need free geospatial data from map images!