#!/usr/bin/python

# post-to-blog.py

import markdown
from xml.etree import ElementTree
from gdata import service
import gdata
import atom
import sys
import getpass
import readline
import ConfigParser

class BlogPost(object):
    """A single posting for a blog owned by a Blogger account

    >>> post = BlogPost('Brian Wisti', 'me@here.com', 'mysecretpassword')
    >>> post.body = 'This is a paragraph'
    >>> print post.body
    <p>This is a paragraph</p>
    """

    def __init__(self, author, account, password):
        self.config = {}
        self.__author = author
        self.__account = account
        self.__password = password
        self.markdown = markdown.Markdown(extensions = ['meta', 'extra', 'codehilite'])
        self.blogger = None

    def parseConfig(self, configText):
        """Reads and stores the directives from the post's config header.

        >>> post = BlogPost('Brian Wisti', 'me@here.com', 'mysecretpassword')
        >>> import os
        >>> myConfig = os.linesep.join(["key1: value1", "key2: value2"])
        >>> post.parseConfig(myConfig)
        >>> post.config['key1']
        'value1'
        >>> post.config['key2']
        'value2'
        """
        textLines = configText.splitlines()
        for line in textLines:
            key, value = line.split(': ')
            self.config[key] = value

    def parsePost(self, postText):
        """Parses the contents of a full post, including header and body.

        >>> import os
        >>> myText = os.linesep.join(["title: Test", "--", "This is a test"])
        >>> post = BlogPost('Brian Wisti', 'me@here.com', 'mysecretpassword')
        >>> post.parsePost(myText)
        >>> print post.config['title']
        Test
        >>> print post.body
        <p>This is a test</p>
        """
        self.raw = postText
        self.body = self.markdown.convert(postText)
        self.meta = self.markdown.Meta

    def login(self):
        if self.blogger == None:
            # Authenticate using ClientLogin
            blogger = service.GDataService(self.__account, self.__password)
            blogger.source = 'post-to-blog.py_v01.0'
            blogger.service = 'blogger'
            blogger.server = 'www.blogger.com'
            blogger.ProgrammaticLogin()
            self.blogger = blogger

        return self.blogger

    def get_blog_id(self):
        blogger = self.login()
         # Get the blog ID
        query = service.Query()
        query.feed = '/feeds/default/blogs'
        feed = blogger.Get(query.ToUri())
        blog_id = feed.entry[0].GetSelfLink().href.split('/')[-1]

        return blog_id

    def create_entry(self):
        # Create the entry to insert.
        entry = gdata.GDataEntry()
        entry.author.append(atom.Author(atom.Name(text=self.__author)))
        entry.title = atom.Title('xhtml', self.meta.get('title', ''))
        entry.content = atom.Content(content_type='html', text=self.body)

        # Assemble labels, if any
        for tag in self.meta.get('tags', []):
            category = atom.Category(term=tag, scheme='http://www.blogger.com/atom/ns#')
            entry.category.append(category)

        # Decide whether this is a draft.
        control = atom.Control()
        control.draft = atom.Draft(text='yes')
        entry.control = control

        return entry

    def sendPost(self, blog_id, entry):
        blogger = self.login()
        blogger.Post(entry, '/feeds/' + blog_id + '/posts/default')

def runTests():
    import doctest
    doctest.testmod()

def parse_cmdline(config):
    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option("-D", "--do-tests", action="store_true", dest="doTests",
                      help="Run built-in doctests")
    parser.add_option("--dry-run", action="store_true", dest="dryRun",
                      help="Do not actually submit to blogger")
    parser.add_option("-f", "--file", dest="filename",
                      help="Specify source file for post")
    parser.add_option("-a", "--author", dest="author",
                      help="The author for this post")
    parser.add_option("-e", "--email", dest="email",
                      help="The email of the blog owner")
    parser.add_option("-p", "--password", dest="password",
                      help="The password of the blog owner")
    parser.add_option("-v", "--verbose", action="store_true", dest="verbose",
                      help="Display marked up file and gdata entry")

    (options, args) = parser.parse_args()
    # Allow command line options to overwrite config settings
    if options.author:
        config.set("connection", "author", options.author)

    if options.email:
        config.set("connection", "email", options.email)

    if options.password:
        config.set("connection", "password", options.password)

    if options.filename:
        config.set("connection", "filename", options.filename)

    if len(args) == 1:
        config.set("connection", "filename", args[0])
    elif len(args) > 1:
        print("Only one filename is allowed.")
        sys.exit(1)

    return options

def ask_user_for_missing_config(config):
    query = {
            'password' : getpass.getpass,
            'author' : raw_input,
            'email' : raw_input,
            'filename' : raw_input
    }
    for option in query.keys():
        try:
            value = config.get("connection", option)
        except ConfigParser.NoOptionError, NameError:
            value = query[option]("%s: " % option)
            config.set("connection", option, value)

    return config


def main():
    config_file = "blog.cfg"
    config = ConfigParser.ConfigParser()
    config.read(config_file)

    options = parse_cmdline(config)

    if options.doTests:
        runTests()
        sys.exit(0)

    ask_user_for_missing_config(config)

    author = config.get("connection", "author")
    email = config.get("connection", "email")
    password = config.get("connection", "password")
    filename = config.get("connection", "filename")

    post = BlogPost(author, email, password)
    postFile = open(filename).read()
    post.parsePost(postFile)

    entry = post.create_entry()

    if options.verbose:
        import pprint
        pprint.pprint(post.meta)
        print(post.body)

    if not options.dryRun:
        blog_id = post.get_blog_id()
        post.sendPost(blog_id)

if __name__ == '__main__':
    main()

