"""Script to load sample medical knowledge base with embeddings"""
import asyncio
from mongodb_client import connect_mongodb, store_medical_knowledge
from embeddings import generate_embedding

# Sample medical knowledge base
MEDICAL_KNOWLEDGE = [
    {
        "title": "Myocardial Infarction (Heart Attack)",
        "specialty": "Cardiology",
        "urgency_indicators": ["chest pain", "shortness of breath", "radiating pain", "sweating", "nausea"],
        "content": """
        Myocardial infarction (MI), commonly known as a heart attack, occurs when blood flow to the heart muscle is blocked.

        Key symptoms:
        - Chest pain or discomfort (often described as pressure, squeezing, or fullness)
        - Pain radiating to shoulders, neck, arms, back, teeth, or jaw
        - Shortness of breath
        - Cold sweats
        - Nausea or vomiting
        - Lightheadedness or dizziness

        Risk factors: High blood pressure, high cholesterol, diabetes, smoking, obesity, family history

        Emergency indicators: Sudden onset of severe chest pain, loss of consciousness
        Urgency level: EMERGENCY - Call 911 immediately

        Initial management: Aspirin (if not allergic), rest, oxygen if available, activate emergency services
        """,
        "differential_diagnoses": ["Angina", "GERD", "Pulmonary embolism", "Aortic dissection"],
        "red_flags": ["Sudden severe chest pain", "Radiating pain", "Shortness of breath", "Diaphoresis"]
    },
    {
        "title": "Appendicitis",
        "specialty": "General Surgery",
        "urgency_indicators": ["right lower abdominal pain", "rebound tenderness", "fever", "nausea"],
        "content": """
        Appendicitis is inflammation of the appendix, requiring surgical intervention.

        Key symptoms:
        - Pain starting near the navel, then moving to right lower abdomen
        - Pain worsens with movement, coughing, or walking
        - Nausea and vomiting
        - Loss of appetite
        - Low-grade fever
        - Abdominal swelling

        Classic sign: McBurney's point tenderness (right lower quadrant)

        Risk factors: Age 10-30, male gender, family history

        Emergency indicators: Severe pain, high fever, rigid abdomen (suggests rupture)
        Urgency level: URGENT - Seek emergency care within hours

        Complications: Ruptured appendix can lead to peritonitis (life-threatening)
        """,
        "differential_diagnoses": ["Gastroenteritis", "Ovarian cyst", "Kidney stones", "Ectopic pregnancy"],
        "red_flags": ["Rigid abdomen", "High fever", "Severe pain", "Rebound tenderness"]
    },
    {
        "title": "Allergic Reaction and Anaphylaxis",
        "specialty": "Emergency Medicine",
        "urgency_indicators": ["difficulty breathing", "swelling", "hives", "throat tightness", "rapid pulse"],
        "content": """
        Allergic reactions range from mild (hives) to severe anaphylaxis (life-threatening).

        Mild-to-moderate symptoms:
        - Hives or skin rash
        - Itching
        - Nasal congestion
        - Watery eyes

        Anaphylaxis symptoms (EMERGENCY):
        - Difficulty breathing or swallowing
        - Swelling of face, lips, tongue, or throat
        - Rapid or weak pulse
        - Dizziness or fainting
        - Severe drop in blood pressure
        - Loss of consciousness

        Common triggers: Foods (peanuts, shellfish), insect stings, medications (penicillin), latex

        Emergency treatment: Epinephrine auto-injector (EpiPen), call 911
        Urgency level: EMERGENCY if anaphylaxis, ROUTINE if mild

        Management: Antihistamines for mild reactions, epinephrine for severe
        """,
        "differential_diagnoses": ["Asthma attack", "Panic attack", "Vasovagal syncope"],
        "red_flags": ["Difficulty breathing", "Swelling of throat", "Rapid pulse", "Loss of consciousness"]
    },
    {
        "title": "Stroke (Cerebrovascular Accident)",
        "specialty": "Neurology",
        "urgency_indicators": ["facial drooping", "arm weakness", "speech difficulty", "sudden confusion"],
        "content": """
        Stroke occurs when blood supply to part of the brain is interrupted or reduced.

        FAST assessment:
        - Face: Facial drooping or numbness
        - Arms: Arm weakness or numbness (especially one side)
        - Speech: Slurred speech or difficulty speaking
        - Time: Time to call 911 immediately

        Additional symptoms:
        - Sudden severe headache
        - Trouble seeing in one or both eyes
        - Difficulty walking, dizziness, loss of balance
        - Confusion or trouble understanding

        Types: Ischemic (clot blocks artery) vs Hemorrhagic (bleeding in brain)

        Risk factors: High blood pressure, diabetes, smoking, atrial fibrillation, high cholesterol

        Emergency indicators: Any FAST symptoms
        Urgency level: EMERGENCY - Every minute counts (golden hour for treatment)

        Treatment window: tPA (clot-busting drug) most effective within 3-4.5 hours
        """,
        "differential_diagnoses": ["TIA", "Migraine with aura", "Seizure", "Brain tumor"],
        "red_flags": ["Sudden onset", "FAST symptoms", "Severe headache", "Loss of consciousness"]
    },
    {
        "title": "Diabetic Ketoacidosis (DKA)",
        "specialty": "Endocrinology",
        "urgency_indicators": ["fruity breath", "rapid breathing", "confusion", "abdominal pain", "vomiting"],
        "content": """
        DKA is a serious complication of diabetes where the body produces excess blood acids (ketones).

        Key symptoms:
        - Excessive thirst and urination
        - Nausea and vomiting
        - Abdominal pain
        - Weakness or fatigue
        - Shortness of breath
        - Fruity-scented breath
        - Confusion or difficulty concentrating

        Warning signs in diabetics:
        - Blood sugar level > 250 mg/dL
        - Ketones in urine
        - Rapid, deep breathing (Kussmaul breathing)

        Triggers: Infection, missed insulin doses, new onset diabetes

        Emergency indicators: Altered mental status, severe dehydration, rapid breathing
        Urgency level: EMERGENCY - Can be life-threatening

        Management: IV fluids, insulin therapy, electrolyte replacement (hospital setting)
        """,
        "differential_diagnoses": ["HHS", "Lactic acidosis", "Uremic acidosis", "Alcohol ketoacidosis"],
        "red_flags": ["Altered consciousness", "Severe dehydration", "Kussmaul breathing", "High blood glucose"]
    },
    {
        "title": "Pneumonia",
        "specialty": "Pulmonology",
        "urgency_indicators": ["fever", "cough", "chest pain", "difficulty breathing", "chills"],
        "content": """
        Pneumonia is an infection that inflames air sacs in one or both lungs.

        Key symptoms:
        - Cough with phlegm (may be green, yellow, or bloody)
        - Fever, sweating, and chills
        - Shortness of breath
        - Chest pain when breathing or coughing
        - Fatigue and weakness
        - Nausea, vomiting, or diarrhea

        Types: Bacterial, viral, or fungal

        Risk factors: Age >65 or <2, chronic diseases, weakened immune system, smoking

        Emergency indicators: High fever, severe breathing difficulty, confusion, bluish lips
        Urgency level: URGENT (can escalate to EMERGENCY in high-risk patients)

        Complications: Respiratory failure, sepsis, lung abscess

        Treatment: Antibiotics for bacterial, supportive care, possible hospitalization
        """,
        "differential_diagnoses": ["Bronchitis", "Tuberculosis", "Lung cancer", "Pulmonary embolism"],
        "red_flags": ["Severe dyspnea", "Hypoxia", "Altered mental status", "Sepsis signs"]
    },
    {
        "title": "Acute Migraine",
        "specialty": "Neurology",
        "urgency_indicators": ["severe headache", "visual disturbances", "nausea", "light sensitivity"],
        "content": """
        Migraine is a neurological condition causing severe recurring headaches.

        Key symptoms:
        - Intense throbbing or pulsing pain (often one-sided)
        - Sensitivity to light and sound
        - Nausea and vomiting
        - Visual disturbances (aura): flashing lights, blind spots, zigzag lines
        - Numbness or tingling

        Phases:
        1. Prodrome: Mood changes, neck stiffness, cravings
        2. Aura: Visual or sensory disturbances (20-60 minutes)
        3. Headache: 4-72 hours if untreated
        4. Postdrome: Fatigue, confusion

        Triggers: Stress, certain foods, hormonal changes, sleep changes, weather

        Red flags requiring immediate evaluation:
        - Sudden severe "thunderclap" headache
        - Headache with fever, stiff neck, confusion, vision loss
        - Headache after head injury
        - New pattern in person over 50

        Urgency level: ROUTINE (unless red flags present)

        Treatment: Pain relievers, triptans, anti-nausea medication, preventive medications
        """,
        "differential_diagnoses": ["Cluster headache", "Tension headache", "Stroke", "Meningitis"],
        "red_flags": ["Thunderclap headache", "Headache with fever", "New onset >50", "Post-trauma"]
    },
    {
        "title": "Gastroesophageal Reflux Disease (GERD)",
        "specialty": "Gastroenterology",
        "urgency_indicators": ["heartburn", "chest pain", "regurgitation", "difficulty swallowing"],
        "content": """
        GERD is chronic acid reflux where stomach acid flows back into the esophagus.

        Key symptoms:
        - Heartburn (burning sensation in chest)
        - Regurgitation of food or sour liquid
        - Difficulty swallowing
        - Sensation of lump in throat
        - Chronic cough or hoarseness
        - Chest pain (can mimic heart attack)

        Warning: GERD chest pain can be difficult to distinguish from cardiac chest pain

        Risk factors: Obesity, pregnancy, smoking, certain foods, hiatal hernia

        Triggers: Spicy foods, citrus, chocolate, caffeine, alcohol, large meals before bed

        Red flags (seek immediate care):
        - Chest pain with shortness of breath, jaw/arm pain, sweating
        - Severe difficulty swallowing
        - Vomiting blood or black tarry stools

        Urgency level: ROUTINE (EMERGENCY if cardiac symptoms present)

        Complications: Esophagitis, Barrett's esophagus, esophageal stricture

        Treatment: Lifestyle changes, antacids, PPIs, H2 blockers
        """,
        "differential_diagnoses": ["Myocardial infarction", "Peptic ulcer", "Esophageal spasm", "Gallbladder disease"],
        "red_flags": ["Cardiac-like chest pain", "Hematemesis", "Dysphagia", "Weight loss"]
    },
    {
        "title": "Urinary Tract Infection (UTI)",
        "specialty": "Urology",
        "urgency_indicators": ["painful urination", "frequent urination", "fever", "back pain", "blood in urine"],
        "content": """
        UTI is an infection in any part of the urinary system (kidneys, bladder, urethra).

        Lower UTI (Cystitis) symptoms:
        - Burning sensation during urination
        - Frequent, urgent need to urinate
        - Cloudy, bloody, or strong-smelling urine
        - Pelvic pain (women)
        - Lower abdominal discomfort

        Upper UTI (Pyelonephritis) symptoms:
        - High fever and chills
        - Flank/back pain
        - Nausea and vomiting
        - General feeling of illness

        Risk factors: Female anatomy, sexual activity, certain birth control, menopause, urinary abnormalities

        Emergency indicators (suggests kidney infection):
        - High fever (>101°F)
        - Severe back or flank pain
        - Vomiting preventing oral intake
        - Signs of sepsis

        Urgency level: ROUTINE for simple UTI, URGENT for pyelonephritis

        Complications: Kidney damage, sepsis, recurrent infections

        Treatment: Antibiotics, increased fluids, pain relief
        """,
        "differential_diagnoses": ["Pyelonephritis", "Kidney stones", "STIs", "Interstitial cystitis"],
        "red_flags": ["High fever", "Flank pain", "Vomiting", "Altered mental status (elderly)"]
    },
    {
        "title": "Asthma Exacerbation",
        "specialty": "Pulmonology",
        "urgency_indicators": ["wheezing", "shortness of breath", "chest tightness", "coughing"],
        "content": """
        Asthma exacerbation is acute worsening of asthma symptoms requiring immediate intervention.

        Key symptoms:
        - Wheezing or whistling sound when breathing
        - Shortness of breath
        - Chest tightness or pain
        - Coughing (especially at night)
        - Difficulty speaking in full sentences
        - Retractions (skin pulling between ribs)

        Severity indicators:
        - Mild: Can speak normally, no retractions
        - Moderate: Speaks in phrases, some retractions
        - Severe: Speaks in words, marked retractions, agitation
        - Life-threatening: Unable to speak, cyanosis, altered consciousness

        Triggers: Allergens, infections, exercise, cold air, stress, pollution

        Emergency indicators:
        - Peak flow <50% of personal best
        - No improvement with rescue inhaler
        - Bluish lips or fingernails
        - Severe breathlessness

        Urgency level: URGENT to EMERGENCY (depending on severity)

        Treatment: Bronchodilators (albuterol), corticosteroids, oxygen, possible hospitalization
        """,
        "differential_diagnoses": ["Anaphylaxis", "COPD exacerbation", "Pneumonia", "Pulmonary embolism"],
        "red_flags": ["Silent chest", "Cyanosis", "Altered consciousness", "Poor response to treatment"]
    }
]


async def load_knowledge():
    """Load medical knowledge into MongoDB with embeddings"""
    try:
        # Connect to MongoDB
        print("🔌 Connecting to MongoDB...")
        await connect_mongodb()

        print(f"\n📚 Loading {len(MEDICAL_KNOWLEDGE)} medical knowledge documents...\n")

        for idx, knowledge in enumerate(MEDICAL_KNOWLEDGE, 1):
            # Generate embedding for the content
            print(f"{idx}. Processing: {knowledge['title']}")

            # Combine title, specialty, and content for embedding
            text_to_embed = f"""
            Title: {knowledge['title']}
            Specialty: {knowledge['specialty']}
            Urgency Indicators: {', '.join(knowledge['urgency_indicators'])}
            Content: {knowledge['content']}
            Differential Diagnoses: {', '.join(knowledge['differential_diagnoses'])}
            Red Flags: {', '.join(knowledge['red_flags'])}
            """

            embedding = generate_embedding(text_to_embed.strip())

            # Add embedding to knowledge data
            knowledge_with_embedding = {
                **knowledge,
                "embedding": embedding,
                "embedding_model": "text-embedding-3-small (OpenAI)",
                "embedding_dimensions": len(embedding)
            }

            # Store in MongoDB
            doc_id = await store_medical_knowledge(knowledge_with_embedding)
            print(f"   ✅ Stored with ID: {doc_id}")

        print(f"\n✨ Successfully loaded {len(MEDICAL_KNOWLEDGE)} medical knowledge documents!")
        print("\n📊 Knowledge base summary:")
        print(f"   - Total documents: {len(MEDICAL_KNOWLEDGE)}")
        print(f"   - Specialties covered: {len(set(k['specialty'] for k in MEDICAL_KNOWLEDGE))}")
        print(f"   - Embedding model: text-embedding-3-small (OpenAI, 1536 dimensions)")

    except Exception as e:
        print(f"\n❌ Error loading knowledge base: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(load_knowledge())
