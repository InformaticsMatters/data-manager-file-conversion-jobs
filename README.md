# data-manager-file-conversion-jobs
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

Data Manager job definitions for file conversions.

## Contributing
The project uses [pre-commit] to enforce rules on files prior to committing
them to the upstream repository. You **MUST** comply with this style to
contribute to the project.

To get started review the pre-commit utility and then setup your local
clone by following the **Installation** and **Quick Start** sections: -

    pip install -r build-requirements.txt
    pre-commit install

Now the project's pre-commit rules will run on every commit, and you can
test everything's OK now with: -

    pre-commit run --all-files

## Testing
Use the Data Manager Job Tester ([jote]) to run tests against the job's
definition, You will need to build the image first: -

    pip install -r build-requirements.txt

    docker-compose build
    jote

And make sure your code passes `pylint`: -

    pylint src

---

[pre-commit]: https://pre-commit.com
[jote]: https://pypi.org/project/im-jote
