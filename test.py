from subprocess import PIPE, STDOUT, Popen

fake_in = StringIO('')
p = Popen(['echo', '\x1b[6n'], stdout=PIPE, stdin=fake_in, stderr=PIPE)
