# Centralized Competitor Feature Specifications

## 1. Context & Objectives
This guide provides centralized functional specifications and manual verification checklists for competitor workflows across OpenClinica and OpenStudyBuilder. By using these checklists, developers can quickly verify parity with competitor clinical systems during local development, reducing lookup times and implementation errors. We aim to support the entire spectrum of features provided by OpenStudyBuilder (Study Design, MDR, Data Standards) and OpenClinica (EDC, Randomization, ePRO, SDV, Data Extraction).

---

## 2. Study Design & MDR Parity (OpenStudyBuilder)

### 2.1 Specification: Study Design & Metadata Repository (MDR)
The system must support the definition and governance of study designs according to CDISC Standards and centralized metadata repositories.
- **Biomedical Concepts (BCs):** Core clinical concepts must be mapable and reusable across protocols.
- **Data Standards Governance:** Ensure CDISC Controlled Terminology (CT) and custom dictionaries can be versioned and applied to study items.
- **Study Elements & Arms:** Support the definition of study arms, cohorts, and elements for complex trial designs (e.g., crossover, adaptive).
- **Value-Level Metadata (VLM):** Ensure granular constraints and attributes at the value level are accurately captured.

### 2.2 Manual Verification Checklist: Study Design & MDR
- [ ] **Step 1:** Define reusable Biomedical Concepts in the metadata repository.
- [ ] **Step 2:** Associate CDISC Controlled Terminology versions with corresponding study items.
- [ ] **Step 3:** Define a complex trial design containing multiple Study Arms, Cohorts, and Elements.
- [ ] **Step 4:** **Verify Biomedical Concepts:** Ensure forms and datasets accurately reflect the mapped BCs.
- [ ] **Step 5:** **Verify Standards Governance:** Ensure forms reject data that violates the applied Controlled Terminology.
- [ ] **Step 6:** **Verify VLM:** Confirm that value-level validations fire appropriately for specific item conditions.

---

## 3. USDM Study Versioning Parity (OpenStudyBuilder)

### 3.1 Specification: USDM Versioning Translation
The system must translate study metadata into CDISC USDM-compatible versioning models.
- **Study Metadata Mapping:** Core study metadata (e.g., Title, Phase, Status) must map strictly to the USDM-defined fields.
- **Version Extraction Rules:** Any mutation to the study design or metadata must trigger a version increment. The updated metadata must map to a new version indicator or `StudyVersion` entity in the underlying models.
- **Graph Immutability:** Instead of overriding existing nodes, the current study status and version details must map to newly versioned nodes in the Neo4j graph, maintaining a clear `PREVIOUS_VERSION` relationship to the prior state.

### 3.2 Manual Verification Checklist: USDM Versioning Model
- [ ] **Step 1:** Start the local development environment and log into the Designer Service.
- [ ] **Step 2:** Create a new Study Protocol with initial metadata and save it to establish the baseline version (Version 1).
- [ ] **Step 3:** Trigger a USDM study metadata export and verify that the output correctly reflects the initial version indicators.
- [ ] **Step 4:** Perform an update to the core study metadata (e.g., update the Phase or Status) and save the changes.
- [ ] **Step 5:** Export the updated study metadata via the local data model output.
- [ ] **Step 6:** **Verify Version Indicator:** Inspect the output and confirm that the version number has correctly incremented and matches the USDM version extraction rules.
- [ ] **Step 7:** **Verify Metadata Translation:** Check that the updated status and metadata accurately map to the core USDM definitions in the new export.
- [ ] **Step 8:** **Verify Graph History:** Query the local graph database to ensure the new version node links to the previous version node via a `PREVIOUS_VERSION` relationship, leaving the historical version intact.

---

## 4. Schedule of Activities (SoA) Parity (OpenStudyBuilder/OpenClinica)

### 4.1 Specification: SoA Definitions
The system must correctly map visits, epochs, and scheduled activities in alignment with CDISC USDM standards.
- **Epochs:** Trial periods (e.g., Screening, Treatment, Follow-up) must map correctly to USDM `Epoch` entities.
- **Visits:** Study visits and encounters must be defined within their respective epochs as `StudyEventDef` entities.
- **Activities:** Clinical procedures and assessments must map to scheduled activities and link to the relevant forms/CRFs.

### 4.2 Manual Verification Checklist: SoA Definitions
- [ ] **Step 1:** Define a study protocol with multiple epochs, visits, and assigned activities.
- [ ] **Step 2:** Export the study definition to USDM format.
- [ ] **Step 3:** **Verify Epochs:** Confirm all defined epochs are correctly mapped.
- [ ] **Step 4:** **Verify Visits:** Ensure study events align with their parent epochs.
- [ ] **Step 5:** **Verify Activities:** Check that scheduled procedures map to the correct CRFs and encounters.

---

## 5. Electronic Data Capture (EDC) & eCRF Parity (OpenClinica)

### 5.1 Specification: Excel CRF Parsing & eCRF Management
The system must correctly parse clinical trial spreadsheets to translate workbook elements into corresponding clinical entities, ensuring full parity with competitor systems:
- **Sheets:** Each sheet within the Excel workbook represents a distinct CRF or form.
- **Sections:** Rows defined as section headers within the sheet are mapped to distinct layout containers or UI sections within the target form.
- **Groups:** Repeating sets of questions (e.g., grids or repeating groups) designated by grouping columns must be mapped to `ItemGroupDef` clinical entities.
- **Items:** Individual question rows are mapped to `ItemDef` clinical entities, translating their associated data types, constraints, and validation rules accordingly.

### 5.2 Manual Verification Checklist: Spreadsheet Import
- [ ] **Step 1:** Start the local development environment.
- [ ] **Step 2:** Prepare a test Excel CRF spreadsheet containing multiple sheets, distinct section headers, grouped variables, and individual items.
- [ ] **Step 3:** Upload the spreadsheet using the local eCRF import interface or API endpoint.
- [ ] **Step 4:** Retrieve the mapped target entities from the local database or Designer UI.
- [ ] **Step 5:** **Verify Sheets:** Check that each sheet in the spreadsheet has correctly translated into a distinct form entity.
- [ ] **Step 6:** **Verify Sections:** Confirm that the section headers have correctly translated into corresponding layout sections within each form.
- [ ] **Step 7:** **Verify Groups:** Ensure that grouped columns are accurately structured as `ItemGroupDef` entities with the correct repeating attributes.
- [ ] **Step 8:** **Verify Items:** Compare the item rows in the spreadsheet against the created `ItemDef` entities, confirming that data types, constraints, and validation rules match exactly.

---

## 6. OpenRosa/Enketo XForm Rendering Parity

### 6.1 Specification: XForm Rendering Rules
The system must render clinical data capture forms compliant with OpenRosa standards.
- **Form UI Controls:** Data constraints and item definitions must map to valid XForm input controls.
- **Relevance & Skip Logic:** Branching logic must correctly map to XForm `relevant` attributes.
- **Calculations:** Computed fields must correctly translate to XForm `calculate` bindings.

### 6.2 Manual Verification Checklist: XForm Rendering
- [ ] **Step 1:** Define a CRF containing conditional logic and calculated fields.
- [ ] **Step 2:** Generate the OpenRosa XForm XML payload.
- [ ] **Step 3:** **Verify UI Controls:** Check that inputs match their defined data types.
- [ ] **Step 4:** **Verify Skip Logic:** Confirm that `relevant` attributes hide/show fields properly.
- [ ] **Step 5:** **Verify Calculations:** Test computed bindings in an Enketo-compatible renderer.

---

## 7. Subject Management & Randomization Parity (OpenClinica)

### 7.1 Specification: Subject State Machine & Randomization
The system must govern participant statuses and enable integrated randomization mechanisms.
- **State Integrity:** Participants can only transition between allowed states (e.g., Enrolled, Active, Completed, Withdrawn).
- **Transition Logs:** Every state change must record the timestamp and responsible user.
- **Randomization:** Integration with RTSM/IWRS systems to allocate treatments securely and blindly upon subject eligibility.

### 7.2 Manual Verification Checklist: Subject Management
- [ ] **Step 1:** Create a test subject in the "Enrolled" state.
- [ ] **Step 2:** Attempt valid and invalid status transitions.
- [ ] **Step 3:** **Verify Integrity:** Confirm invalid transitions are rejected by the system.
- [ ] **Step 4:** **Verify Transition Logs:** Ensure valid state changes are recorded accurately.
- [ ] **Step 5:** **Verify Randomization:** Confirm that upon marking a subject as "Eligible", the randomization module successfully assigns an appropriate arm/treatment without unblinding the investigator.

---

## 8. Query Management & Discrepancy Notes Parity (OpenClinica)

### 8.1 Specification: Query Workflows
The system must support the complete lifecycle of clinical data queries (Open, Answered, Closed, Reassigned) and discrepancy management.
- **Query Creation:** Automated cross-form edit checks and manual reviewers can flag discrepancies.
- **Query Resolution:** Sites can provide answers, which data managers can subsequently close or re-open.
- **SDV Integration:** Queries can be created during Source Data Verification (SDV) to flag source-to-CRF inconsistencies.

### 8.2 Manual Verification Checklist: Query Management
- [ ] **Step 1:** Trigger a validation discrepancy on an eCRF via an edit check to generate a query.
- [ ] **Step 2:** Submit an answer to the query as a Site User.
- [ ] **Step 3:** **Verify Workflow:** Ensure the query state moves from "Open" to "Answered".
- [ ] **Step 4:** **Verify Resolution:** Close the query as a Data Manager and confirm it is locked.
- [ ] **Step 5:** **Verify SDV Queries:** Flag an item during SDV and verify a Discrepancy Note is instantiated.

---

## 9. Medical Coding & Dictionary Integration Parity (OpenClinica)

### 9.1 Specification: Medical Coding Workflows
The system must support auto-coding and manual coding for terms such as Adverse Events and Concomitant Medications.
- **Dictionary Support:** MedDRA and WHODrug dictionary integrations must be supported.
- **Auto-Coding:** The system must match verbatim terms to dictionary lowest level terms (LLT) where an exact match exists.
- **Manual Coding:** Synonym lists and up-versioning mechanisms must be available for medical coders to handle non-exact matches.

### 9.2 Manual Verification Checklist: Medical Coding
- [ ] **Step 1:** Enter a verbatim term into an Adverse Event CRF that exactly matches a MedDRA LLT.
- [ ] **Step 2:** **Verify Auto-Coding:** Check that the system automatically assigns the corresponding MedDRA code and hierarchical terms (PT, SOC, etc.).
- [ ] **Step 3:** Enter an ambiguous verbatim term.
- [ ] **Step 4:** **Verify Manual Coding:** Confirm that a Medical Coder role can search the dictionary, apply the correct code manually, and save the term to a synonym list.

---

## 10. Data Extraction & Exporting Parity (OpenClinica)

### 10.1 Specification: Export Formats
The system must provide industry-standard exports for biostatistics and archival.
- **CDISC ODM-XML:** Extracted data and metadata must strictly adhere to the Operational Data Model schema.
- **CDISC SDTM / Dataset-JSON:** Output mapped clinical data dynamically to standard submission formats.
- **SPSS/SAS/CSV:** Support flat and structured file exports for statistical analysis.

### 10.2 Manual Verification Checklist: Data Extraction
- [ ] **Step 1:** Populate multiple subjects and CRFs with test data.
- [ ] **Step 2:** Execute a data export job selecting CDISC ODM-XML and Dataset-JSON.
- [ ] **Step 3:** **Verify ODM-XML:** Validate the XML against the CDISC ODM XSD schema.
- [ ] **Step 4:** **Verify SDTM/Dataset-JSON:** Check that datasets align with the requested SDTM mappings and structures.

---

## 11. Patient Reported Outcomes (ePRO) Parity (OpenClinica)

### 11.1 Specification: ePRO & Wearables
The system must support direct patient data entry through specialized portals or device integrations.
- **Patient Portals:** Secure, simplified UIs adapted for patient entry (mobile-responsive).
- **Notifications:** SMS and email reminders for upcoming questionnaires.
- **BYOD/Wearables:** Support for passive data ingestion (e.g., activity trackers, continuous glucose monitors).

### 11.2 Manual Verification Checklist: ePRO
- [ ] **Step 1:** Provision a subject for ePRO and trigger a questionnaire notification.
- [ ] **Step 2:** **Verify Notifications:** Confirm the SMS/Email contains a valid, secure link.
- [ ] **Step 3:** **Verify Portal Access:** Complete the questionnaire via a mobile viewport.
- [ ] **Step 4:** **Verify Data Flow:** Confirm the responses are instantly available within the clinical database, flagged as patient-entered source data.

---

## 12. Security, Permissions, and Part 11 Audit Log Parity

### 12.1 Specification: 21 CFR Part 11 Compliance
The system must capture comprehensive, immutable audit trails, electronic signatures, and enforce Role-Based Access Control (RBAC).
- **Audit Logs:** Capture `created_at`, `created_by`, `reason_for_change`, and `version_index`. Audit records must be immutable.
- **Electronic Signatures:** Support affidavit agreements and re-authentication to sign off on CRFs or casebooks.
- **RBAC & Site Segregation:** Roles (Site, Investigator, CRA, Data Manager) must strictly limit visibility. Sites cannot see other sites' data.

### 12.2 Manual Verification Checklist: Compliance & Security
- [ ] **Step 1:** Perform a data mutation (e.g., update a clinical observation).
- [ ] **Step 2:** **Verify Audit Log:** Ensure the database audit row contains the correct user, timestamp, and reason, and that the API rejects attempts to modify it.
- [ ] **Step 3:** Attempt to sign a CRF as an Investigator.
- [ ] **Step 4:** **Verify Electronic Signature:** Ensure the system requires re-authentication (e.g., password prompt) before stamping the signature.
- [ ] **Step 5:** Log in as a Site User for Site A and attempt to access a subject at Site B.
- [ ] **Step 6:** **Verify Site Segregation:** Confirm access to Site B's data is blocked.
