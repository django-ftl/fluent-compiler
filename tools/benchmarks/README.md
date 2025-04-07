To run the benchmarks, after installing the project in the normal way
for development, run any of the benchmarks you want as scripts:

    $ ./runtime.py
    $ ./compiler.py

You can also run them using py.test with extra args:

    $ pytest --benchmark-warmup=on runtime.py -k interpolation

The “plural form” tests are the cases where GNU gettext performs most
favourably, partly because it uses a much simpler (and incorrect) function for
deciding plural forms, while we use the more complex ones from CLDR. You can
exclude those by doing:

    $ pytest --benchmark-warmup=on runtime.py -k 'not plural'

To profile the benchmark suite, we recommend py-spy as a good tool. Install
py-spy: https://github.com/benfred/py-spy

Then do something like this to profile the benchmark. Depending on your
platform, you might need to use `sudo`.

    $ py-spy -f prof.svg -- py.test --benchmark-warmup=off runtime.py

And look at prof.svg in a browser. Note that this diagram includes the fixture
setup, warmup and calibration phases which you should ignore.

This directory also contains generate_ftl_file.py, which can be used to generate
files for benchmarking against. It can be run a python file:

    $ python generate_ftl_file.py outfile.ftl

For full command line options, use:

    $ python generate_ftl_file.py -h
