To run the benchmarks, do the following from this directory:

    $ pip install -r requirements.txt

Then, run any of the benchmarks you want as scripts:

    $ ./runtime.py
    $ ./compiler.py

You can also run them using py.test with extra args:

    $ py.test --benchmark-warmup=on runtime.py -k interpolation

To profile the benchmark suite, we recommend py-spy as a
good tool. Install py-spy: https://github.com/benfred/py-spy

Then do something like this to profile the benchmark. Depending on your
platform, you might need to use `sudo`.

    $ py-spy -f prof.svg -- py.test --benchmark-warmup=off runtime.py

And look at prof.svg in a browser. Note that this diagram includes the fixture
setup, warmup and calibration phases which you should ignore.
