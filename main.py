import streamlit as st
import numpy as np
import aubio
from streamlit_webrtc import webrtc_streamer, AudioProcessorBase, WebRtcMode

# Global constants
scale_to_midi = {
    'C': 60, 'C#': 61, 'D': 62, 'D#': 63, 'E': 64, 'F': 65,
    'F#': 66, 'G': 67, 'G#': 68, 'A': 69, 'A#': 70, 'B': 71
}
swar_semitones = [0, 2, 4, 5, 7, 9, 11]
swar_names = ['Sa', 'Re', 'Ga', 'Ma', 'Pa', 'Dha', 'Ni']
saptak_names = {-1: 'Mandra', 0: 'Madhya', 1: 'Taar'}
swar_to_semitone = {swar: semitone for swar, semitone in zip(swar_names, swar_semitones)}

def find_closest_swar(m):
    semitones = swar_semitones + [12]
    distances = [min(abs(m - s), 12 - abs(m - s)) for s in semitones]
    min_dist_idx = np.argmin(distances)
    if min_dist_idx == 7:  # Closest to 12
        return 'Sa', 1  # Sa of next saptak
    return swar_names[min_dist_idx], 0

class AudioProcessor(AudioProcessorBase):
    def __init__(self):
        self.pitch_detector = aubio.pitch("default", 2048, 2048 // 2, 44100)
        self.pitch_detector.set_unit("Hz")
        self.pitch_detector.set_silence(-40)

    def recv(self, frame):
        audio_data = frame.to_ndarray().astype(np.float32)
        frequency = self.pitch_detector(audio_data)[0]
        return frequency

def process_audio(frame):
    frequency = frame
    if frequency > 20:
        n = 69 + 12 * np.log2(frequency / 440)
        d = n - n_Sa
        k = int(np.floor(d / 12))
        m = d - 12 * k
        swar, k_adjust = find_closest_swar(m)
        k += k_adjust
        saptak = saptak_names.get(k, f"Saptak {k}")

        # Calculate clarity
        semitone_offset = swar_to_semitone[swar]
        n_exact = n_Sa + 12 * k + semitone_offset
        f_exact = 440 * 2**((n_exact - 69) / 12)
        cents = 1200 * np.log2(frequency / f_exact)
        abs_cents = abs(cents)

        if abs_cents < 10:
            clarity = 'green'
        elif abs_cents < 20:
            clarity = 'yellow'
        else:
            clarity = 'red'

        # Display
        freq_placeholder.write(f"**Frequency:** {frequency:.2f} Hz")
        saptak_placeholder.write(f"**Saptak:** {saptak}")
        swar_placeholder.markdown(f'**Swar:** <span style="color:{clarity}">{swar}</span>', unsafe_allow_html=True)
    else:
        freq_placeholder.write("**Frequency:** No sound detected")
        saptak_placeholder.write("**Saptak:** -")
        swar_placeholder.markdown('**Swar:** -', unsafe_allow_html=True)

def main():
    st.title("Hindustani Flute Note Detection")
    scale = st.selectbox("Select your flute's scale", list(scale_to_midi.keys()), index=0)
    global n_Sa
    n_Sa = scale_to_midi[scale]

    st.write("""
    ### How it works:
    - Select your flute's scale from the dropdown.
    - Play your flute near your microphone.
    - The app will display the detected frequency, saptak, and swar in real-time.
    - The swar is color-coded based on clarity:
      - **Green**: Clear (within 10 cents)
      - **Yellow**: Somewhat clear (within 20 cents)
      - **Red**: Not clear (more than 20 cents)
    - Uses Bilawal thaat (shuddha swars) for note mapping.
    """)

    global freq_placeholder, saptak_placeholder, swar_placeholder
    freq_placeholder = st.empty()
    saptak_placeholder = st.empty()
    swar_placeholder = st.empty()

    webrtc_streamer(
        key="flute-note-detection",
        mode=WebRtcMode.RECVONLY,
        audio_processor_factory=AudioProcessor,
        async_processing=True,
        callbacks={"on_audio": process_audio},
    )

if __name__ == "__main__":
    main()
