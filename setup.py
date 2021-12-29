import setuptools
import glob

from mautrix_telegram.get_version import git_tag, git_revision, version, linkified_version

with open("requirements.txt") as reqs:
    install_requires = reqs.read().splitlines()

try:
    long_desc = open("README.md").read()
except IOError:
    long_desc = "Failed to read README.md"

with open("mautrix_telegram/version.py", "w") as version_file:
    version_file.write(f"""# Generated in setup.py

git_tag = {git_tag!r}
git_revision = {git_revision!r}
version = {version!r}
linkified_version = {linkified_version!r}
""")

setuptools.setup(
    name="mautrix-telegram",
    version=version,
    url="https://github.com/mautrix/telegram",

    author="Tulir Asokan",
    author_email="tulir@maunium.net",

    description="A Matrix-Telegram hybrid puppeting/relaybot bridge.",
    long_description=long_desc,
    long_description_content_type="text/markdown",

    packages=setuptools.find_packages(),

    install_requires=install_requires,
    python_requires="~=3.7",

    classifiers=[
        "Development Status :: 4 - Beta",
        "License :: OSI Approved :: GNU Affero General Public License v3 or later (AGPLv3+)",
        "Topic :: Communications :: Chat",
        "Framework :: AsyncIO",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
    package_data={"mautrix_telegram": [
        "web/public/*.mako", "web/public/*.png", "web/public/*.css",
        "example-config.yaml",
    ]},
    data_files=[
        (".", ["alembic.ini", "mautrix_telegram/example-config.yaml"]),
        ("alembic", ["alembic/env.py"]),
        ("alembic/versions", glob.glob("alembic/versions/*.py"))
    ],
)
