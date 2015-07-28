{-# LANGUAGE OverloadedStrings, RecordWildCards #-}
module Main where

import Data.Aeson
import Text.Pandoc
import System.ZMQ4.Monadic
import Control.Monad
import Data.ByteString.Char8 (pack, unpack)
import Data.ByteString.UTF8 (fromString, toString)
import Data.ByteString.Lazy (fromStrict)
import Control.Concurrent (threadDelay)
import Control.Applicative ((<$>))
import Text.Blaze.Html.Renderer.String
import Debug.Trace
 
data Job = Job {informat :: String, outformat :: String, payload :: String}

instance FromJSON Job where
  parseJSON = withObject "job" $ \o -> do
    	informat <- o .: "informat"
    	outformat <- o .: "outformat"
	payload <- o .: "payload"
	return Job{..}

readToPandoc :: Job -> Maybe Pandoc
readToPandoc job = do
	case (informat job) of
		"markdown" -> Just (readMarkdown def (payload job))
		"json" -> Just (readJSON def (payload job))
		"docbook" -> Just (readDocBook def (payload job))
		_ -> Nothing

writeFromPandoc :: Job -> Pandoc -> String
writeFromPandoc job pandoc = do
	case (outformat job) of
		"json" -> writeJSON def pandoc
		"markdown" -> writeMarkdown def pandoc
		"html" -> renderHtml (writeHtml def pandoc)
		_ -> "Unsupported output format"
	
myActualConvert :: Job -> String
myActualConvert job = do
		let pandoc = readToPandoc job
		case pandoc of
			Just value -> writeFromPandoc job value
			Nothing -> "Unsupported input format"

myConvert :: Maybe Job -> String
myConvert job = do
		case job of
			Just job -> myActualConvert job
			Nothing -> "Invalid json"

main :: IO ()
main = do
    runZMQ $ do
        repSocket <- socket Rep
        bind repSocket "tcp://*:5555"
  
        forever $ do
            msg <- receive repSocket
	    let x = decode (fromStrict msg)
            send repSocket [] (fromString (myConvert x))
