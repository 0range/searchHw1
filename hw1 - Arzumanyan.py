import urllib.request as request
from time import sleep, time
from html.parser import HTMLParser
from os.path import abspath
import heapq
import copy
import math
import string


MAXITER = 300000
SLEEP_TIME = 1
LINKSTART = 'http://simple.wikipedia.org'


class LinkExtractor(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.links_collection = set()

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            for name, value in attrs:
                if name == 'href':
                    self.links_collection.add(value)

    def getLinks(self):
        return self.links_collection


class TextExtractor(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.isNeeded = True
        self.text = ""
        
    def handle_starttag(self, tag, attrs):
        if tag == 'script' or tag == 'style':
            self.isNeeded = False

    def handle_endtag(self, tag):
        self.isNeeded = True
 
    def handle_data(self, data):
        if self.isNeeded:
            self.text += " " + data

    def get_text(self):
        self.text = ' '.join(self.text.split())
        return self.text


def isWikiArticle(link):
    return (link[:len(LINKSTART)] == LINKSTART) and \
            'action=' not in link and\
            'oldid=' not in link and\
            '/Talk:' not in link and\
            '/User:' not in link and\
            'WhatLinksHere' not in link and\
            'title=Special' not in link and\
            'Wikipedia:Simple_talk' not in link and\
            '/File:' not in link and\
            'Special:RecentChangesLinked' not in link and\
            '&printable=yes' not in link and\
            'index.php?' not in link and\
            '#' not in link and\
            '/Special:' not in link and\
            '/Template:' not in link and\
            '/User_talk:' not in link and\
            '/Wikipedia:' not in link


def completeLink(current_link, new_link):
    # cases: absolute (// - add protocol name),
    # relative: to whole site or to the page,
    # ancor(return itself), protocol (return itself), script (return itself)
    res = new_link
    # replace // with http:// OR https:// for absolute
    if len(new_link) > 2 and new_link[:2] == '//':
        res = current_link[:current_link.find('/')] + new_link
    # relative just on site
    elif len(new_link) > 1 and new_link[:1] == '/':
        res = LINKSTART + new_link
    # relative from page
    elif len(new_link) > 1\
             and new_link[:1] != '/'\
             and new_link[:1] != '#'\
             and '//' not in new_link\
             and ':' not in new_link:
        res = current_link + new_link
    return res


def log(inputstring):
    print(inputstring)
    with open('download.log', 'a') as outputfile:
        outputfile.write(inputstring + '\n')


def download(start_page):
    print('Starting download...')
    iterator = 1
    new_pages = {start_page}
    visited_pages = {}
    while len(new_pages) > 0 and iterator < MAXITER:
        log('List to visit size : ' + str(len(new_pages)))
        current_page = new_pages.pop()
        successfull = True
        pages_to_visit = []
        try:
            pages_to_visit = processPage(current_page, iterator)
        except:
            log('Error on page: ' + current_page)
            successfull = False
        visited_pages[current_page] = (iterator, successfull)
        for el in pages_to_visit:
            saveLink(iterator, el)
            if el not in visited_pages:
                new_pages.add(el)
        iterator += 1
        sleep(SLEEP_TIME)
    return visited_pages


def processPage(page, iterator):
    path = downloadPage(page, iterator)
    links = set(map(lambda x: completeLink(page, x), extractLinksPage(path)))
    links = set(filter(isWikiArticle, links))
    # print('\n', 'from page', page, '\ngot ', len(links), ' links: \n', links)
    return links


def downloadPage(page, iterator):
    url = request.urlopen(page)
    path = 'docs/' + str(iterator) + '.html'
    with open(path, 'w') as outputfile:
        outputfile.write(url.read().decode('utf-8'))
    log('Downloaded page #' + str(iterator) + ' from: ' + page)
    return path


def extractLinksPage(path):
    extractor = LinkExtractor()
    html = request.urlopen('file://' + abspath(path)).read().decode('utf-8')
    extractor.feed(html)
    return extractor.getLinks()


def saveUrls(urls):
    with open('docs/urls', 'w') as outputfile:
        for el in urls:
            outputfile.write(str(el) + '\t')
            for i in urls[el]:
                outputfile.write(str(i) + '\t')
            outputfile.write('\n')


def saveLink(currentlink, nextlink):
    with open('linkspathes.tsv', 'a') as outputfile:
        outputfile.write(str(currentlink) + '\t' + nextlink + '\n')


def downloadSimpleWiki():
    start_page = 'http://simple.wikipedia.org/wiki/'
    start_time = time()
    res = download(start_page)
    print('Finished\n')
    print(time() - start_time)
    saveUrls(res)
    print(time() - start_time)
          

def linkIsBad(linkname):
    return '/Category:'                         in linkname or\
           '/Wikipedia_talk:'                   in linkname or\
           '/Category_Talk:'                    in linkname or\
           '/Help:'                             in linkname or\
           '/Media:'                            in linkname or\
           '/MediaWiki:'                        in linkname or\
           '/MediaWiki_Talk:'                   in linkname or\
           'http://simple.wikipedia.org/?diff=' in linkname or\
           '/Module:'                           in linkname or\
           '/Template_talk:'                    in linkname


def saveGraph(urls):
    oldnum = 0
    starttime = time()
    values = set(urls.values())
    with open('graph.dat', 'w') as graphfile:
        with open('linkspathes.tsv', 'r') as halffile:
            for newline in halffile:
                newlist = newline.strip().split()
                if int(newlist[0]) != oldnum and oldnum % 100 == 0:
                    print(int(newlist[0]), time() - starttime)
                oldnum = int(newlist[0])
                if newlist[1] in urls and int(newlist[0]) in values:
                    graphfile.write(str(newlist[0]) + '\t' + str(urls[newlist[1]]) + '\n')


def getSize(docno):
    path = 'docs/' + str(docno) + '.html'
    size = 0
    with open(path, 'r') as fileobj:
        size += len(fileobj.read())
    return size

def getUrls():
    res = dict()
    with open('docs/urls', 'r') as urlsfile:
        for newline in urlsfile:
            if newline.strip().split()[2] == 'True':#and not linkIsBad(newline.strip().split()[0]):
                res[newline.strip().split()[0]] = int(newline.strip().split()[1])
    return res


def saveUrls(urls):
    with open('urls.dat', 'w') as urlsfile:
        for el in urls:
            urlsfile.write(str(urls[el]) + '\t' + el + '\n')
    

def convertHTML(docno):
    path = 'docs/' + str(docno) + '.html'
    extractor = TextExtractor()
    html = request.urlopen('file://' + abspath(path)).read().decode('utf-8')
    extractor.feed(html)
    savepath = 'text/' + str(docno) + '.txt'
    with open(savepath, 'w') as savefile:
        savefile.write(extractor.get_text())
    return 0


def saveSizes(sizes):
    with open('sizes.dat', 'w') as sizesfile:
        for el in sizes:
            sizesfile.write(str(el) + '\t' + str(sizes[el]) + '\n')


def processText(urls):
    res = 0
    thetime = time()
    sizes = dict()
    steps = 0
    for el in urls:
        if not linkIsBad(el):
            try:
                sizes[urls[el]] = getSize(urls[el])
                convertHTML(urls[el])
            except:
                with open('processError.log', 'a') as errlg:
                    errlg.write(str(el) + str(urls[el]) + '\n')
                print('Some error.')
                res += 1
            steps += 1
            if steps % 1000 == 0:
                print('Done: ', steps, 'in', time() - thetime, 's')
    saveSizes(sizes)
    return res


def process():
    thetime = time()
    urls = getUrls()
    saveUrls(urls)
    print('Processing graph...')
    saveGraph(urls)
    print(time() - thetime)
    print('Processing text...')
    res = processText(urls)
    print(time() - thetime)
    return res


def loadGraph(path):
    graph = []
    prev = 0
    enumeration = []
    with open(path, 'r') as graphfile:
        i = 0
        for newline in graphfile:
            edge = newline.strip().split()
            if int(edge[0]) != prev:
                prev = int(edge[0])
                enumeration.append(prev)
            graph.append([int(edge[0]), int(edge[1])])
            i += 1
            if i % 200000 == 0:
                print('Loading', i)
    rest = []
    got = set(enumeration)
    i = 0
    for edge in graph:
        if edge[1] not in got:
            rest.append(edge[1])
        i += 1
        if i % 200000 == 0:
            print('Updating', i)
    for el in list(set(rest)):
        enumeration.append(el)
    return graph, enumeration


def convertGraph(graph, enumeration):
    converted_graph = []
    for i in range(len(enumeration)):
        converted_graph.append([])
    lookup = dict()
    for i in range(len(enumeration)):
        lookup[enumeration[i]] = i
    i = 0
    for edge in graph:
        i += 1
        if i % 200000 == 0:
            print('Converting', i)
        converted_graph[lookup[edge[0]]].append(lookup[edge[1]])
    return converted_graph


def savePathes(pathes, enumeration):
    with open('patheslengths.tsv', 'w') as outputfile:
        for i in range(len(pathes)):
            outputfile.write(str(enumeration[i]) + '\t' + str(pathes[i]) + '\n')


def saveRanks(ranks, enumeration):
    with open('ranks.tsv', 'w') as outputfile:
        for i in range(len(ranks)):
            outputfile.write(str(enumeration[i]) + '\t' + str(ranks[i]) + '\n')


def l2norm(a, b):
    res = 0
    for i in range(len(a)):
        res += (a[i] - b[i]) ** 2
    return math.sqrt(res)


def pageRank(graph):
    eps = 0.0000001
    ranks = [] 
    for i in range(len(graph)):
        ranks.append(1. / len(graph))
    thetime = time()
    step = 0 
    while True:
        print('PageRank steps', step, 'in', time() - thetime)
        step += 1 

        oldranks = copy.deepcopy(ranks)
        for i in range(len(graph)):
            out = len(graph[i])
            for j in range(out):
                ranks[graph[i][j]] += oldranks[i] / out
        norm = 1. / sum(ranks)
        for i in range(len(ranks)):
            ranks[i] *= norm
        difference = l2norm(oldranks, ranks)
        if difference < eps:
            break
        print(difference)
    return ranks


def dijkstraOptimized(graph):
    starttime = time()
    infty = 10 ** 9
    n = len(graph)
    s = 0
    dist = [infty] * n
    dist[s] = 0
    heap = []
    heapq.heappush(heap, [0, s])
    stepnum = 0
    while len(heap) > 0:
        stepnum += 1
        print('Dijkstra opt', stepnum, 'in', time() - starttime)
        current_pair = heapq.heappop(heap)
        if current_pair[0] > dist[current_pair[1]]:
            continue
        #print('Dijkstra opt', stepnum, 'in', time() - starttime)
        for i in range(len(graph[current_pair[1]])):
            v = graph[current_pair[1]][i]
            if dist[v] > dist[current_pair[1]] + 1:
                dist[v] = dist[current_pair[1]] + 1
                heapq.heappush(heap, [dist[v], v])        
    return dist


def degrees(graph):
    outdegrees = dict()
    indegrees = dict()
    for el in graph:
        if el[0] in outdegrees:
            outdegrees[el[0]] += 1
        else:
            outdegrees[el[0]] = 1
        if el[1] in indegrees:
            indegrees[el[1]] += 1
        else:
            indegrees[el[1]] = 1
    return indegrees, outdegrees


def saveDegrees(path, degrees, enumeration):
    degs = copy.deepcopy(degrees)
    for el in enumeration:
        if el not in degs:
            degs[el] = 0
    with open(path, 'w') as outputfile:
        for el in degs:
            outputfile.write(str(el) + '\t' + str(degs[el]) + '\n')


def graphprocess():

    thetime = time()
    print('Loading...')
    (graph, enumeration) = loadGraph('graph.dat')
    print('Loaded in', time() - thetime)
    
    thetime = time()
    print('Saving degrees...')
    (indegrees, outdegrees) = degrees(graph)
    saveDegrees('indegrees.tsv', indegrees, enumeration)
    saveDegrees('outdegrees.tsv', outdegrees, enumeration)
    print('Saved in', time() - thetime)

    thetime = time()
    print('Converting...')
    converted_graph = convertGraph(graph, enumeration)
    print('Converted in', time() - thetime)

    thetime = time()
    print('Searching pathes...')
    pathes = dijkstraOptimized(converted_graph)
    print('Completed search in', time() - thetime)

    thetime = time()
    print('Saving pathes...')
    savePathes(pathes, enumeration)
    print('Saved in', time() - thetime)

    thetime = time()
    print('Searching ranks...')
    ranks = pageRank(converted_graph)
    print('Converged in', time() - thetime)

    print('Saving ranks...')
    saveRanks(ranks, enumeration)
    print('Saved in', time() - thetime)


def getIndexes(path):
    indexes = set()
    with open(path, 'r') as graphfile:
        for newline in graphfile:
            indexes.add(int(newline.strip().split()[0]))
            indexes.add(int(newline.strip().split()[1]))
    return indexes    


def processWords(indexes):
    words = dict()
    thetime = time()
    translator = dict()
    for el in string.punctuation:
        translator[ord(el)] = " "
    for i in indexes:
        path = 'text/' + str(i) + '.txt'
        print('Reading', path, time() - thetime)
        with open(path, 'r') as inputfile:
            for line in inputfile:
                linewords = line.translate(translator).strip().split()
                for word in linewords:
                    if word in words:
                        words[word] += 1
                    else:
                        words[word] = 1
    return words


def saveWords(words):
    with open('wordfreq.tsv', 'w') as outputfile:
        for word in words:
            outputfile.write(word + '\t' + str(words[word]) + '\n')


def words():
    indexes = getIndexes('graph.dat')
    print('Got indexes')
    words = processWords(indexes)
    print('Saving')
    saveWords(words)


def main():
    downloadSimpleWiki()
    process()
    graphprocess()
    words()


if __name__ == '__main__':
    main()
