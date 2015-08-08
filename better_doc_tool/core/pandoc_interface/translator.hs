module Translator() where

import Text.Pandoc
import Foreign.C.Types
import Foreign.C.String
import System.IO.Unsafe
import Text.Blaze.Html.Renderer.String

foreign export ccall hs_markdown_to_json :: CString -> IO CString
foreign export ccall hs_markdown_to_html :: CString -> IO CString
foreign export ccall hs_json_to_html :: CString -> IO CString
foreign export ccall hs_docbook_to_markdown :: CString -> IO CString

markdown_to_json :: String -> String
markdown_to_json str = 
	writeJSON def (readMarkdown def str)

json_to_html :: String -> String
json_to_html str =
	renderHtml (writeHtml def (readJSON def str))

docbook_to_markdown :: String -> String
docbook_to_markdown str =
	writeMarkdown def (readDocBook def str)

markdown_to_html :: String -> String
markdown_to_html str =
	renderHtml (writeHtml def (readMarkdown def str))

hs_markdown_to_json :: CString -> IO CString
hs_markdown_to_json str = newCString (markdown_to_json (unsafePerformIO (peekCString str)))

hs_json_to_html :: CString -> IO CString
hs_json_to_html str = newCString (json_to_html (unsafePerformIO (peekCString str)))

hs_docbook_to_markdown :: CString -> IO CString
hs_docbook_to_markdown str = newCString (docbook_to_markdown (unsafePerformIO (peekCString str)))

hs_markdown_to_html :: CString -> IO CString
hs_markdown_to_html str = newCString (markdown_to_html (unsafePerformIO (peekCString str)))
