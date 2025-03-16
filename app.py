import os
import subprocess
import whisper
from gtts import gTTS
import requests
import streamlit as st

# Cache the Whisper model
@st.cache_resource
def load_whisper_model():
    return whisper.load_model("tiny")

# Streamlit UI
st.set_page_config(page_title="AI Video English Dubbing Studio", page_icon="🎥", layout="centered")
st.title("🎬 AI Video English Dubbing Studio using gTTS and Zonos AI")
st.markdown("**Transform non-English videos into English-dubbed content with ease!**")

# Upload video file
uploaded_file = st.file_uploader("📤 Upload a video file (Supported formats: MP4, MOV, AVI)", type=["mp4", "mov", "avi"])

if uploaded_file is not None:
    st.write("📽️ Processing the video...")

    # Save the uploaded video temporarily
    with open("temp_video.mp4", "wb") as f:
        f.write(uploaded_file.read())
    temp_video_path = "temp_video.mp4"

    # Step 1: Extract audio using FFmpeg
    with st.spinner("🔊 Extracting audio from the video..."):
        audio_file_path = "temp_audio.wav"
        subprocess.run(["ffmpeg", "-i", temp_video_path, "-q:a", "0", "-map", "a", audio_file_path])

    # Step 2: Transcribe audio using Whisper
    with st.spinner("📝 Transcribing audio using Whisper..."):
        model = load_whisper_model()
        result = model.transcribe(audio_file_path, task="translate")
        transcription = result["text"]

    # Step 3: Generate English audio using gTTS
    with st.spinner("🎤 Generating English audio using gTTS..."):
        tts = gTTS(transcription, lang="en")
        english_audio_gtts_path = "english_audio_gtts.mp3"
        tts.save(english_audio_gtts_path)

    # Step 4: Generate English audio using Zonos
    with st.spinner("🎤 Generating English audio using Zonos AI..."):
        zonos_api_key = "zsk-38eff65061c1219a17da4d60c27448d29fe705e8a65f432c6f7edf46c0cba0d7"
        zonos_url = "http://api.zyphra.com/v1/audio/text-to-speech"

        zonos_payload = {
            "text": transcription,
            "language_iso_code": "en-us",
            "speaking_rate": 15,
            "model": "zonos-v0.1-transformer",
            "mime_type": "audio/mp3"
        }

        headers = {
            "X-API-Key": zonos_api_key,
            "Content-Type": "application/json"
        }

        zonos_response = requests.post(zonos_url, json=zonos_payload, headers=headers)

        if zonos_response.status_code == 200:
            english_audio_zonos_path = "english_audio_zonos.mp3"
            with open(english_audio_zonos_path, "wb") as f:
                f.write(zonos_response.content)
        else:
            st.error(f"❌ Failed to generate Zonos audio. Error: {zonos_response.status_code} - {zonos_response.text}")
            english_audio_zonos_path = None

    # Step 5: Replace original audio with gTTS and Zonos audio using FFmpeg
    if english_audio_zonos_path:
        with st.spinner("🔄 Replacing original audio with gTTS and Zonos audio..."):
            # Output video with gTTS audio
            output_video_gtts_path = "output_video_gtts.mp4"
            ffmpeg_command_gtts = [
                "ffmpeg",
                "-i", temp_video_path,
                "-i", english_audio_gtts_path,
                "-map", "0:v:0",  # Map video from the first input
                "-map", "1:a:0",  # Map audio from the second input
                "-c:v", "copy",
                "-c:a", "aac",
                "-strict", "experimental",
                output_video_gtts_path
            ]
            process_gtts = subprocess.run(ffmpeg_command_gtts, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            # Output video with Zonos audio
            output_video_zonos_path = "output_video_zonos.mp4"
            ffmpeg_command_zonos = [
                "ffmpeg",
                "-i", temp_video_path,
                "-i", english_audio_zonos_path,
                "-map", "0:v:0",  # Map video from the first input
                "-map", "1:a:0",  # Map audio from the second input
                "-c:v", "copy",
                "-c:a", "aac",
                "-strict", "experimental",
                output_video_zonos_path
            ]
            process_zonos = subprocess.run(ffmpeg_command_zonos, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            # Check if both outputs were created successfully
            if process_gtts.returncode == 0 and process_zonos.returncode == 0:
                st.success("✅ Processing completed.")

                # Display gTTS output
                st.write("### gTTS Output")
                st.video(output_video_gtts_path)
                st.download_button("⬇️ Download gTTS Dubbed Video", data=open(output_video_gtts_path, "rb"), file_name="gtts_dubbed_video.mp4")

                # Display Zonos output
                st.write("### Zonos Output")
                st.video(output_video_zonos_path)
                st.download_button("⬇️ Download Zonos Dubbed Video", data=open(output_video_zonos_path, "rb"), file_name="zonos_dubbed_video.mp4")
            else:
                st.error("❌ Failed to generate one or both output videos. Check the error logs below:")
                st.code(process_gtts.stderr.decode())
                st.code(process_zonos.stderr.decode())
        else:
            st.error("❌ Zonos audio generation failed. Skipping Zonos output.")

    # Clean up temporary files
    os.remove(temp_video_path)
    os.remove(audio_file_path)
    os.remove(english_audio_gtts_path)
    if english_audio_zonos_path:
        os.remove(english_audio_zonos_path)
