# Part 2 — Preparing the Spreadsheet and Importing Tasks with a Local Python Virtual Environment

In this part, we assume you already have:

* a running Label Studio instance
* an administrator account and API token
* one spreadsheet workbook with two sheets:

  * `users`
  * `tasks`

Label Studio supports API- and SDK-based project creation and task import, and the Python SDK is the recommended way to automate these steps from local scripts. ([Label Studio][1])

## Goal

We will prepare a workflow in which:

* annotators are listed in a `users` sheet
* project texts are listed in a `tasks` sheet
* each text has already been distributed to annotators
* a local Python script reads the spreadsheet
* the script creates one Label Studio project per annotator per project
* the script imports the assigned tasks through the API

This approach works well in Label Studio Community because task import is fully supported through the API and SDK. ([Label Studio][1])

## Recommended workbook structure

Create one Excel workbook, for example:

```text
annotation_workbook.xlsx
```

with these sheets:

### Sheet 1 — `users`

Use the following columns:

| email                                         | first_name | last_name | password      |
| --------------------------------------------- | ---------- | --------- | ------------- |
| [joao@example.com](mailto:joao@example.com)   | João       | Silva     | StrongPass123 |
| [maria@example.com](mailto:maria@example.com) | Maria      | Souza     | StrongPass123 |
| [pedro@example.com](mailto:pedro@example.com) | Pedro      | Lima      | StrongPass123 |

This sheet will be used by the import script to provision annotator accounts.

### Sheet 2 — `tasks`

Use the following columns:

| project_code | project_title | external_id | text                                          | annotator_1                                 | annotator_2                                   | annotator_3                                   | batch | source     |
| ------------ | ------------- | ----------- | --------------------------------------------- | ------------------------------------------- | --------------------------------------------- | --------------------------------------------- | ----- | ---------- |
| ner_health   | NER Health    | doc_0001    | O paciente apresentou febre e dor no peito.   | [joao@example.com](mailto:joao@example.com) | [maria@example.com](mailto:maria@example.com) | [pedro@example.com](mailto:pedro@example.com) | b1    | hospital_a |
| ner_health   | NER Health    | doc_0002    | O exame indicou pneumonia no pulmão esquerdo. | [joao@example.com](mailto:joao@example.com) | [maria@example.com](mailto:maria@example.com) | [pedro@example.com](mailto:pedro@example.com) | b1    | hospital_a |
| ner_legal    | NER Legal     | doc_0101    | O autor ajuizou ação contra a União.          | [joao@example.com](mailto:joao@example.com) | [maria@example.com](mailto:maria@example.com) | [pedro@example.com](mailto:pedro@example.com) | b2    | tribunal_x |

Notes:

* `external_id` should be stable and unique inside each dataset.
* `text` can remain in Portuguese.
* `annotator_1`, `annotator_2`, and `annotator_3` indicate who should annotate that document.
* `project_code` helps separate different annotation campaigns.

## Create a local Python virtual environment

Label Studio can also be installed with Python and virtual environments, and its documentation recommends using a standard Python `venv` workflow for local environments. ([Label Studio][2])

On your local machine, create a directory for the import scripts:

```bash
mkdir labelstudio-import
cd labelstudio-import
```

Create the virtual environment:

```bash
python3 -m venv .venv
```

Activate it on Linux or macOS:

```bash
source .venv/bin/activate
```

Upgrade `pip`:

```bash
python -m pip install --upgrade pip
```

Install the required packages:

```bash
pip install pandas openpyxl requests
```

## Create the NER label configuration

Label Studio projects are driven by a labeling configuration, and project setup requires defining that interface before importing tasks. ([Label Studio][3])

Create a file named `label_config_ner.xml`:

```xml
<View>
  <Labels name="label" toName="text">
    <Label value="DISEASE" background="#f8b4b4"/>
    <Label value="SYMPTOM" background="#ffd59e"/>
    <Label value="MEDICATION" background="#b7f0ad"/>
    <Label value="ANATOMY" background="#a8d8ff"/>
  </Labels>
  <Text name="text" value="$text"/>
</View>
```

This configuration lets the annotator select a span in the text and then assign a label, which is the standard NER-style workflow in Label Studio. Label Studio supports configurable labeling interfaces and project templates through its project setup flow. ([Label Studio][4])

## Create the import script

See file `import_from_workbook.py`.

## Why this structure is useful

Each imported task keeps its metadata inside the `data` section, including:

* `project_code`
* `project_title`
* `external_id`
* `assigned_annotator_email`

Label Studio’s import flow accepts JSON tasks and stores task data for later annotation and export. The official documentation also notes that the Python SDK and API are designed for these project and task automation workflows. ([Label Studio][5])

## Run the script

Inside the active virtual environment:

```bash
python import_from_workbook.py
```

If everything is correct, the script will:

* create the annotator accounts
* create projects as needed
* import the assigned texts into the correct projects

## What happens in Label Studio

After running the script, Label Studio will contain projects named like this:

```text
ner_health :: NER Health :: joao@example.com
ner_health :: NER Health :: maria@example.com
ner_health :: NER Health :: pedro@example.com
ner_legal :: NER Legal :: joao@example.com
...
```

This naming scheme makes it easy to separate:

* the annotation campaign
* the project domain
* the annotator responsible for that project copy

## Example of an imported task

A task imported by the script looks like this:

```json
{
  "data": {
    "project_code": "ner_health",
    "project_title": "NER Health",
    "external_id": "doc_0001",
    "text": "O paciente apresentou febre e dor no peito.",
    "batch": "b1",
    "source": "hospital_a",
    "assigned_annotator_email": "joao@example.com"
  }
}
```

This is consistent with Label Studio’s task import model, which expects JSON task objects and supports additional metadata fields inside `data`. ([Label Studio][5])

## Summary

At this point, you have:

* a local Python virtual environment
* an Excel workbook with `users` and `tasks`
* an automated import script
* one Label Studio project per annotator and per project code
* imported Portuguese texts ready for NER annotation

The next part should cover exporting annotations back into spreadsheets and computing agreement at the document-label level.

[1]: https://labelstud.io/guide/sdk "Label Studio Python SDK"
[2]: https://labelstud.io/guide/install.html "Install and Upgrade Label Studio"
[3]: https://labelstud.io/guide/setup_project "Label Studio Documentation — Set up your labeling project"
[4]: https://labelstud.io/guide/get_started "Label Studio Documentation — Overview of Label Studio"
[5]: https://labelstud.io/guide/tasks.html "Import Data into Label Studio"
