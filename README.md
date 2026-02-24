> work in progress

# Book Club Pages

This repository is used to create a static webpage via GitHub pages for a book club (e.g. for the [SFF Zirkel](https://rue-a.github.io/sff-zirkel/)). The page is generated on the basis of the contents of `data/books.json` and `club.json`. It defines GitHub Actions and GitHub Issue templates to add and review books without the need to code. The `add-book` action runs a Python script that queries the [Open Library](https://openlibrary.org/) API, which allows to fetch book metadata via ISBN or book-title. 

## setup
- update action permissions ("Allow all actions and reusable workflows" and "Allow GitHub Actions to create and approve pull requests")
- all people who want to contribute via issue have to be "Collaborators" (repository settings)
- add book label
- add review label
- make sure you main branch actually has the label `main` (not `master` or something)
- activate GitHub Pages


# References 

This software uses the [tufte-css](https://github.com/edwardtufte/tufte-css) classes.