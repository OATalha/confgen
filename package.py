
name = "confgen"

version = "0.0.1"

build_command = 'python -m rezutil build {root} --ignore backup'
private_build_requires = ["rezutil"]

requires = [
        "python-3",
        "GitPython",
        "PyGithub"
]


def commands():
    env.PYTHONPATH.prepend("{root}/python")

    alias("confgen", "python -m confgen")
