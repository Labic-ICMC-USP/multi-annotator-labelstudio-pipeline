# Multi-Annotator NER Pipeline with Label Studio Community Edition

This project provides a practical pipeline for **Named Entity Recognition (NER)** annotation with **multiple annotators** using **Label Studio Community Edition**.

The main goal is to help teams set up a shared annotation environment that is easy to reproduce, easy to maintain, and suitable for collaborative data labeling. This is especially useful in research and applied NLP projects where annotation quality, user management, and data persistence are important.

A multi-annotator setup is important because it allows:

- collaboration among several annotators in the same project
- better control of annotation workflows
- later analysis of agreement and annotation quality
- more reliable dataset construction for NER tasks

To support this workflow, the project is organized into simple parts.

## Project Structure

- [Part 1 — Installing Label Studio with Docker and PostgreSQL](./part1.md)  
  Setup of Label Studio Community Edition with Docker and PostgreSQL for a more robust multi-user environment.

- [Part 2 — Creating the NER Project and Labeling Configuration](./part2.md)  
  Creation of the NER annotation project and definition of the labeling interface.

## Why this project

Many annotation tutorials focus only on local or single-user setups. In practice, NER projects often require:

- more than one annotator
- persistent storage
- project organization
- API access for automation
- a setup that can be reused in future datasets

This repository was designed to address these needs with a straightforward and reproducible approach.

## Expected outcome

By following the tutorial, you will have:

- a running Label Studio instance
- PostgreSQL as the backend database
- persistent storage for annotations and metadata
- a NER project ready for collaborative annotation
- a foundation for future automation with the Label Studio API

## Audience

This tutorial is useful for:

- NLP researchers
- data science teams
- students building annotation datasets
- practitioners preparing custom NER corpora

## Notes

This project uses **Label Studio Community Edition** and focuses on a practical self-hosted setup. It is intended as a simple starting point that can later be extended with reverse proxy, HTTPS, backups, and integration scripts.

## Next steps

Start with [Part 1](./part1.md), then continue to [Part 2](./part2.md).
