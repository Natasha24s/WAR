# app.py

import streamlit as st
import requests
import json
import base64
from PIL import Image
import io
import time

# Configure API endpoint
API_ENDPOINT = "https://inpj25o2h9.execute-api.us-east-1.amazonaws.com/prod/generate"

def convert_to_jpeg(image):
    """Convert image to JPEG format"""
    if image.mode in ('RGBA', 'LA'):
        # Remove alpha channel if present
        background = Image.new('RGB', image.size, (255, 255, 255))
        background.paste(image, mask=image.split()[-1])
        image = background
    elif image.mode != 'RGB':
        image = image.convert('RGB')
    
    # Convert to JPEG
    jpeg_img = io.BytesIO()
    image.save(jpeg_img, format='JPEG', quality=95)
    return jpeg_img.getvalue()

def validate_image_size(image_bytes):
    """Validate image size (max 5MB)"""
    MAX_SIZE = 5 * 1024 * 1024  # 5MB
    return len(image_bytes) <= MAX_SIZE

def analyze_architecture(image_bytes):
    try:
        # Convert image to JPEG and then to base64
        jpeg_bytes = convert_to_jpeg(Image.open(io.BytesIO(image_bytes)))
        base64_image = base64.b64encode(jpeg_bytes).decode('utf-8')
        
        # Prepare the request payload
        payload = {
            'image': base64_image
        }
        
        # Make API request
        response = requests.post(
            API_ENDPOINT,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=300  # 5-minute timeout
        )
        
        if response.status_code == 200:
            return response.json().get('analysis')
        else:
            st.error(f"API Error: {response.status_code}")
            if response.json().get('error'):
                st.error(f"Error details: {response.json()['error']}")
            return None
            
    except requests.exceptions.Timeout:
        st.error("Request timed out. Please try again.")
        return None
    except Exception as e:
        st.error(f"Error: {str(e)}")
        return None

def parse_analysis_results(analysis_text):
    if not analysis_text:
        st.error("No analysis text received from the API")
        return None

    # Debug: Show raw response
    st.write("Raw Response:")
    st.code(analysis_text)

    results = {
        'Operational Excellence': {'strengths': [], 'risks': [], 'risk_level': '', 'recommendations': []},
        'Security': {'strengths': [], 'risks': [], 'risk_level': '', 'recommendations': []},
        'Reliability': {'strengths': [], 'risks': [], 'risk_level': '', 'recommendations': []},
        'Performance Efficiency': {'strengths': [], 'risks': [], 'risk_level': '', 'recommendations': []},
        'Cost Optimization': {'strengths': [], 'risks': [], 'risk_level': '', 'recommendations': []},
        'Sustainability': {'strengths': [], 'risks': [], 'risk_level': '', 'recommendations': []}
    }

    # Split into lines and find table rows
    lines = analysis_text.split('\n')
    current_pillar = None
    
    for line in lines:
        line = line.strip()
        if not line or line.startswith('| ---'):  # Skip empty lines and separator rows
            continue

        # Process table rows
        if line.startswith('|'):
            parts = [part.strip() for part in line.split('|')]
            parts = [p for p in parts if p]  # Remove empty strings
            
            if len(parts) >= 5:
                pillar_name = parts[0]
                # Check if this is a pillar we're tracking
                for known_pillar in results.keys():
                    if known_pillar in pillar_name:
                        current_pillar = known_pillar
                        # Split the content by bullet points if they exist
                        strengths = [s.strip('- ') for s in parts[1].split('<br>')]
                        risks = [r.strip('- ') for r in parts[2].split('<br>')]
                        risk_level = parts[3]
                        recommendations = [rec.strip('- ') for rec in parts[4].split('<br>')]
                        
                        # Update results
                        results[current_pillar]['strengths'] = [s for s in strengths if s]
                        results[current_pillar]['risks'] = [r for r in risks if r]
                        results[current_pillar]['risk_level'] = risk_level
                        results[current_pillar]['recommendations'] = [rec for rec in recommendations if rec]
                        break

    # Validate results
    has_content = False
    for pillar_data in results.values():
        if any(pillar_data.values()):
            has_content = True
            break
    
    if not has_content:
        st.error("Failed to parse the analysis results properly")
        return None

    return results

def display_results(results):
    """Display the analysis results in a formatted way"""
    if not results:
        return

    # Display each pillar's analysis
    for pillar, details in results.items():
        if any(details.values()):  # Only show pillars with content
            st.subheader(pillar)
            
            # Create formatted table data
            df_data = {
                'Strengths': ['\n'.join(details['strengths'])],
                'Risks': ['\n'.join(details['risks'])],
                'Risk Level': [details['risk_level']],
                'Recommendations': ['\n'.join(details['recommendations'])]
            }
            
            # Display table
            st.table(df_data)
    
    # Display high-priority items
    st.subheader("High Priority Items")
    high_priority_items = [
        f"{pillar}: {rec}" 
        for pillar, details in results.items() 
        for rec in details['recommendations'] 
        if details['risk_level'].upper() == 'HIGH'
    ]
    
    if high_priority_items:
        for item in high_priority_items:
            st.write(f"- {item}")
    else:
        st.write("No high-priority items identified.")

def create_download_link(results):
    """Create a formatted report for download"""
    report = []
    report.append("AWS Well-Architected Framework Analysis Report")
    report.append("=" * 50 + "\n")
    
    for pillar, details in results.items():
        if any(details.values()):
            report.append(f"\n{pillar}")
            report.append("-" * len(pillar))
            report.append("\nStrengths:")
            for strength in details['strengths']:
                report.append(f"- {strength}")
            report.append("\nRisks:")
            for risk in details['risks']:
                report.append(f"- {risk}")
            report.append(f"\nRisk Level: {details['risk_level']}")
            report.append("\nRecommendations:")
            for rec in details['recommendations']:
                report.append(f"- {rec}")
            report.append("\n")

    report.append("\nHigh Priority Items")
    report.append("=" * 20)
    high_priority_items = [
        f"{pillar}: {rec}" 
        for pillar, details in results.items() 
        for rec in details['recommendations'] 
        if details['risk_level'].upper() == 'HIGH'
    ]
    if high_priority_items:
        for item in high_priority_items:
            report.append(f"- {item}")
    else:
        report.append("No high-priority items identified.")

    return "\n".join(report)

def main():
    st.set_page_config(
        page_title="AWS Well-Architected Review Tool",
        page_icon="🔍",
        layout="wide"
    )

    st.title("AWS Well-Architected Review Tool")
    st.write("Upload an AWS architecture diagram for automated analysis based on the Well-Architected Framework.")

    # File uploader
    uploaded_file = st.file_uploader(
        "Upload AWS Architecture Diagram", 
        type=['png', 'jpg', 'jpeg'],
        help="Upload a clear diagram of your AWS architecture. Supported formats: PNG, JPG, JPEG"
    )
    
    if uploaded_file is not None:
        try:
            # Read image
            image_bytes = uploaded_file.read()
            
            # Validate image size
            if not validate_image_size(image_bytes):
                st.error("Image size must be less than 5MB")
                return
                
            # Display the uploaded image
            image = Image.open(io.BytesIO(image_bytes))
            st.image(image, caption='Uploaded Architecture Diagram', use_column_width=True)
            
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                if st.button("Analyze Architecture", use_container_width=True):
                    with st.spinner("Analyzing architecture... This may take a few minutes."):
                        # Create a progress bar
                        progress_bar = st.progress(0)
                        for i in range(100):
                            time.sleep(0.1)
                            progress_bar.progress(i + 1)
                        
                        # Get analysis from API
                        analysis_result = analyze_architecture(image_bytes)
                        
                        if analysis_result:
                            # Parse and display results
                            results = parse_analysis_results(analysis_result)
                            if results:
                                st.success("Analysis completed successfully!")
                                display_results(results)
                                
                                # Create download buttons for different formats
                                col1, col2 = st.columns(2)
                                with col1:
                                    # JSON download
                                    result_json = json.dumps(results, indent=2)
                                    st.download_button(
                                        label="Download JSON Results",
                                        data=result_json,
                                        file_name="architecture_analysis.json",
                                        mime="application/json"
                                    )
                                with col2:
                                    # Text report download
                                    report_text = create_download_link(results)
                                    st.download_button(
                                        label="Download Text Report",
                                        data=report_text,
                                        file_name="architecture_analysis_report.txt",
                                        mime="text/plain"
                                    )
                        
        except Exception as e:
            st.error(f"Error processing image: {str(e)}")
            st.write("Stack trace:")
            st.exception(e)

    # Add footer
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center'>
            <p>AWS Well-Architected Review Tool | Built with Streamlit and Amazon Bedrock</p>
        </div>
        """,
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()
