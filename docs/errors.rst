Error handling
==============

The Fluent philosophy is to try to recover from errors, and not throw
exceptions, on the basis that a partial translation is usually better than one
that is entirely missing or a crash.

fluent-compiler adopts that philosophy, but also tries to abide by the Zen of
Python - “Errors should never pass silently. Unless explicitly silenced.”

The combination of these two different philosophies works as follows:

* Errors made by **translators** in the contents of FTL files do not raise
  exceptions. Instead the errors are collected in an ``errors`` list, and some
  kind of substitute string is returned. For example, if a non-existent term
  ``-brand-name`` is referenced from a message, the string ``-brand-name`` is
  inserted into the returned string.

  Also, if the translator uses a function and passes the wrong number of
  positional arguments, or unavailable keyword arguments, this error will be
  caught and reported, without allowing the exception to propagate.

* Exceptions triggered by **developer** errors (whether the authors of
  fluent-compiler or a user of fluent-compiler) are not caught, but are allowed to
  propagate. For example:

  * An incorrect message ID passed to ``FluentBundle.format`` is most likely a
    developer error (a typo in the message ID), and so causes an exception to be
    raised.

    A message ID that is correct but missing in some languages will cause the
    same error, but it is expected that to cover this eventuality
    ``FluentBundle.format`` will be wrapped with functions that automatically
    perform fallback to languages that have all messages defined. This fallback
    mechanism is currently not implemented in ``fluent_compiler`` itself (see
    `issue 1 <https://github.com/django-ftl/fluent-compiler/issues/1>`_).

  * Message arguments of unexpected types, such as passing a string argument to
    a message that uses ``NUMBER`` on it, will raise exceptions, since it is the
    developer's job to ensure the right arguments are being passed to the
    message function.

  * Exceptions raised by custom functions are also assumed to be developer
    errors (as documented in :doc:`functions`, these functions should not raise
    exceptions), and are not caught.
