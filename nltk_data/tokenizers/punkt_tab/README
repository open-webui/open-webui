Pretrained Punkt Models -- Jan Strunk (New version trained after issues 313 and 514 had been corrected)

Most models were prepared using the test corpora from Kiss and Strunk (2006). Additional models have
been contributed by various people using NLTK for sentence boundary detection.

For information about how to use these models, please confer the tokenization HOWTO:
http://nltk.googlecode.com/svn/trunk/doc/howto/tokenize.html
and chapter 3.8 of the NLTK book:
http://nltk.googlecode.com/svn/trunk/doc/book/ch03.html#sec-segmentation

There are pretrained tokenizers for the following languages:

File                Language            Source                             Contents                Size of training corpus(in tokens)           Model contributed by
=======================================================================================================================================================================
czech.pickle        Czech               Multilingual Corpus 1 (ECI)        Lidove Noviny                   ~345,000                             Jan Strunk / Tibor Kiss
                                                                           Literarni Noviny
-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
danish.pickle       Danish              Avisdata CD-Rom Ver. 1.1. 1995     Berlingske Tidende              ~550,000                             Jan Strunk / Tibor Kiss
                                        (Berlingske Avisdata, Copenhagen)  Weekend Avisen
-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
dutch.pickle        Dutch               Multilingual Corpus 1 (ECI)        De Limburger                    ~340,000                             Jan Strunk / Tibor Kiss
-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
english.pickle      English             Penn Treebank (LDC)                Wall Street Journal             ~469,000                             Jan Strunk / Tibor Kiss
                    (American)
-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
estonian.pickle     Estonian            University of Tartu, Estonia       Eesti Ekspress                  ~359,000                             Jan Strunk / Tibor Kiss
-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
finnish.pickle      Finnish             Finnish Parole Corpus, Finnish     Books and major national        ~364,000                             Jan Strunk / Tibor Kiss
                                        Text Bank (Suomen Kielen           newspapers
                                        Tekstipankki)
                                        Finnish Center for IT Science
                                        (CSC)
-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
french.pickle       French              Multilingual Corpus 1 (ECI)        Le Monde                        ~370,000                             Jan Strunk / Tibor Kiss
                    (European)
-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
german.pickle       German              Neue Zürcher Zeitung AG            Neue Zürcher Zeitung            ~847,000                             Jan Strunk / Tibor Kiss
                    (Switzerland)       CD-ROM
                    (Uses "ss"
                     instead of "ß")
-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
greek.pickle        Greek               Efstathios Stamatatos              To Vima (TO BHMA)               ~227,000                             Jan Strunk / Tibor Kiss
-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
italian.pickle      Italian             Multilingual Corpus 1 (ECI)        La Stampa, Il Mattino           ~312,000                             Jan Strunk / Tibor Kiss
-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
norwegian.pickle    Norwegian           Centre for Humanities              Bergens Tidende                 ~479,000                             Jan Strunk / Tibor Kiss
                    (Bokmål and         Information Technologies,
                     Nynorsk)           Bergen
-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
polish.pickle       Polish              Polish National Corpus             Literature, newspapers, etc.  ~1,000,000                             Krzysztof Langner
                                        (http://www.nkjp.pl/)
-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
portuguese.pickle   Portuguese          CETENFolha Corpus                  Folha de São Paulo              ~321,000                             Jan Strunk / Tibor Kiss
                    (Brazilian)         (Linguateca)
-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
slovene.pickle      Slovene             TRACTOR                            Delo                            ~354,000                             Jan Strunk / Tibor Kiss
                                        Slovene Academy for Arts
                                        and Sciences
-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
spanish.pickle      Spanish             Multilingual Corpus 1 (ECI)        Sur                             ~353,000                             Jan Strunk / Tibor Kiss
                    (European)
-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
swedish.pickle      Swedish             Multilingual Corpus 1 (ECI)        Dagens Nyheter                  ~339,000                             Jan Strunk / Tibor Kiss
                                                                           (and some other texts)
-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
turkish.pickle      Turkish             METU Turkish Corpus                Milliyet                        ~333,000                             Jan Strunk / Tibor Kiss
                                        (Türkçe Derlem Projesi)
                                        University of Ankara
-----------------------------------------------------------------------------------------------------------------------------------------------------------------------

The corpora contained about 400,000 tokens on average and mostly consisted of newspaper text converted to
Unicode using the codecs module.

Kiss, Tibor and Strunk, Jan (2006): Unsupervised Multilingual Sentence Boundary Detection.
Computational Linguistics 32: 485-525.

---- Training Code ----

# import punkt
import nltk.tokenize.punkt

# Make a new Tokenizer
tokenizer = nltk.tokenize.punkt.PunktSentenceTokenizer()

# Read in training corpus (one example: Slovene)
import codecs
text = codecs.open("slovene.plain","Ur","iso-8859-2").read()

# Train tokenizer
tokenizer.train(text)

# Dump pickled tokenizer
import pickle
out = open("slovene.pickle","wb")
pickle.dump(tokenizer, out)
out.close()

---------
