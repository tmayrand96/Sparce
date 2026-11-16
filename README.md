# 📊 Sparce AI — Module GAR (Gestion des activités de remplacement)

**Documentation Produit & Procédure Opérationnelle Standard (POS / SOP)**  
**Public cible :** Gestionnaires d'opérations, planificateurs d'horaires, analystes RH et Direction des Ressources Technologiques et Informationnelles (DRTI).

---

## 🎯 Objectif Opérationnel

**Sparce AI (Module GAR)** est une solution d'aide à la décision et d'optimisation des effectifs. Cette plateforme automatise la réconciliation entre les données de présence réelles et les cibles opérationnelles, détecte les écarts critiques par quart de travail et génère des livrables stratégiques d'arbitrage et d'affectation destinés aux Ressources Humaines.

---

## 🔄 Architecture du Flux Opérationnel (Logigramme)

Le diagramme ci-dessous illustre le cycle complet de traitement, de la saisie terrain jusqu'à la génération conditionnelle des rapports décisionnels :

```mermaid
flowchart TD
 %%{init: {
  'theme': 'base',
  'themeVariables': {
    'background': '#f4f9fd',
    'primaryColor': '#ffffff',
    'primaryBorderColor': '#0073A9',
    'primaryTextColor': '#0f2942',
    'lineColor': '#005b87',
    'clusterBkg': '#eaf4fc',
    'clusterBorder': '#7ab8db',
    'fontFamily': 'Segoe UI, Helvetica, Arial, sans-serif',
    'fontSize': '13px'
  },
  'flowchart': {
    'curve': 'basis',
    'padding': 16,
    'nodeSpacing': 35,
    'rankSpacing': 50,
    'htmlLabels': true
  }
}}%%
flowchart LR
    %% Classes de style harmonisées (Palette Bleu Sparce AI)
    classDef step fill:#ffffff,stroke:#0073A9,stroke-width:1.5px,color:#0f2942;
    classDef engine fill:#d8eefb,stroke:#005b87,stroke-width:2px,stroke-dasharray: 5 5,color:#003b5c,font-weight:bold;
    classDef condition fill:#cbe6f9,stroke:#026aa7,stroke-width:2px,color:#00334e,font-weight:bold;
    classDef governance fill:#e3effd,stroke:#1e56a0,stroke-width:2px,color:#163172,font-weight:bold;
    classDef output fill:#e1f5fe,stroke:#0288d1,stroke-width:2px,color:#01579b,font-weight:bold;
    classDef api fill:#e0f2f1,stroke:#00796b,stroke-width:2px,stroke-dasharray: 5 5,color:#004d40,font-weight:bold;

    subgraph P1 ["1. Saisie & Extraction (SIRH)"]
        direction TB
        A["Extraction Virtuo Lourd<br/>(Feuilles quotidiennes)"]:::step
        B["Saisie des présences<br/>(JOUR / SOIR / NUIT)"]:::step
        C["Classeurs normalisés :<br/>• JOUR-XX-XX.xlsx<br/>• SOIR-XX-XX.xlsx<br/>• NUIT-XX-XX.xlsx"]:::step
        A --> B --> C
    end

    subgraph P2 ["2. Ingestion & Moteur Déterministe (RAM)"]
        direction TB
        D["Importation multi-fichiers<br/>(Excel Workforce Workbook)"]:::step
        E["Sélection de la période<br/>(Calendrier interactif)"]:::step
        F["Sélecteur de quart<br/>(J / S / N / Tous)"]:::step
        G[["⚙️ Conciliation déterministe<br/>Présences vs Ratios (RAM)<br/>Zéro persistance"]]:::engine
        D --> E --> F --> G
    end

    subgraph P3 ["3. Gouvernance, Livrables & Extension API"]
        direction TB
        H["🛡️ Audit Human-in-the-Loop<br/>Validation par l'agent"]:::governance
        I{"Portée du<br/>quart ?"}:::condition
        J["Affichage des écarts<br/>Quart unique (J/S/N)"]:::output
        K["📥 Download Topo 24h<br/>Synthèse multi-quarts (.md)"]:::output
        L[["🔌 Connect to API (Optionnel)<br/>Clé API institutionnelle<br/>(ex. Azure OpenAI)<br/>Rapports & KPIs de gestion"]]:::api

        H --> I
        I -- "Quart unique" --> J
        I -- "Tous les quarts" --> K
        H -. "Connecteur gouverné" .-> L
    end

    C ==> D
    G ==> H
```

---

## 📋 Procédure Opérationnelle Étape par Étape

### Étape 1 : Saisie des données de présence (JOUR, SOIR, NUIT)
1. **Accès aux feuilles quotidiennes :** Ouvrez le classeur de suivi et accédez aux onglets d'entrée journaliers (`LUNDI`, `MARDI`, `SAMEDI`, etc.).
2. **Saisie opérationnelle :** Renseignez les données de présence effectives pour le quart de travail correspondant.
3. **Nomenclature d'enregistrement :** Enregistrez systématiquement les classeurs selon la convention normalisée afin d'assurer l'ingestion multi-quarts :
   * `JOUR-XX-XX.xlsx`
   * `SOIR-XX-XX.xlsx`
   * `NUIT-XX-XX.xlsx`

---

### Étape 2 : Importation et traitement dans Sparce AI (Module GAR)
1. **Lancement :** Ouvrez l'application web **Sparce AI — Module GAR**.
2. **Ingestion des fichiers :** Cliquez sur le bouton **Importer** et sélectionnez simultanément ou individuellement vos classeurs `.xlsx` (Jour, Soir, Nuit).
3. **Configuration du rapport (Volet de navigation latéral) :**
   * **Sélecteur de date(s) :** Sélectionnez la période cible. Le moteur exécute immédiatement et automatiquement le rapprochement *Présences vs Cibles*.
   * **Sélecteur de quart :** Filtrez sur un quart précis (`JOUR`, `SOIR`, `NUIT`) ou sélectionnez **`Tous les quarts`** pour une consolidation sur 24 heures. Le recalcul matriciel s'opère instantanément à chaque changement de sélection.

---

### Étape 3 : Interrogation et génération du conseil décisionnel
1. **Analyse interactive :** Utilisez le volet d'analyse / invite de commande de Sparce AI pour interroger directement les données chargées (identification des déficits d'effectifs, détection des goulots d'étranglement et points de friction opérationnels).
2. **Optimisation et arbitrage RH :** Cliquez sur le bouton **`Generate Personalized Workforce Report`** pour exécuter le moteur d'optimisation et produire les recommandations structurées d'arbitrage et de réaffectation.
3. **Exportation du bilan consolidé (Conditionnel) :**
   * Lorsque le **Sélecteur de quart** est positionné sur **`Tous les quarts`**, l'interface active l'option d'exportation globale.
   * Cliquez sur **Télécharger le rapport « Topo 24h – global »** pour extraire la synthèse complète couvrant l'ensemble du cycle de 24 heures.

---

## 🏛️ Gouvernance & Valeur Ajoutée (DRTI / Gestion Opérationnelle)

| Dimension | Bénéfice Opérationnel |
| :--- | :--- |
| **Intégrité des données** | Ingestion directe des classeurs `.xlsx` originaux sans manipulation intermédiaire ni perte de formules. |
| **Réactivité temps réel** | Recalcul dynamique des écarts *Présences vs Cibles* dès l'ajustement du **Sélecteur de date(s)** ou du **Sélecteur de quart**. |
| **Affichage contextuel intelligent** | Le livrable **« Topo 24h – global »** est verrouillé tant que la vue consolidée **« Tous les quarts »** n'est pas active, éliminant tout risque d'exportation partielle ou biaisée. |
| **Standardisation RH** | Production homogène des recommandations d'affectation via le moteur **Generate Personalized Workforce Report**. |

---
*Web app designed and optimized by Tristan Mayrand*
