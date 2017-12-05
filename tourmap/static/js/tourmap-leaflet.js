"use strict";

var mapStateMaker = function(mapId, activities, mapSettings, popupMaker) {
  var _map = L.map(mapId);
  var _mapElement = $("#" + mapId);
  var _activities = activities;
  var _mapSettings = mapSettings;
  var _popupMaker = popupMaker;

  var _markersPlaced = false;
  var _markers = [];
  var _polyLines = [];

  var _currentMapHeight = 0;


  function viewSetup() {
    var corner1 = L.latLng(_mapSettings["bounds"]["corner1"]);
    var corner2 = L.latLng(_mapSettings["bounds"]["corner2"]);
    var maxCorner1 = L.latLng(_mapSettings["max_bounds"]["corner1"]);
    var maxCorner2 = L.latLng(_mapSettings["max_bounds"]["corner2"]);

    var initialLat = (corner1.lat + corner2.lat) / 2.0;
    var initialLng = (corner1.lng + corner2.lng) / 2.0;

    _map.setView([initialLat, initialLng], 1, {animate: false});
    _map.setMaxBounds([maxCorner1, maxCorner2]);
  };

  function fitBounds() {
    var maxCorner1 = L.latLng(_mapSettings["max_bounds"]["corner1"]);
    var maxCorner2 = L.latLng(_mapSettings["max_bounds"]["corner2"]);
    _map.fitBounds([maxCorner1, maxCorner2], {animate: true});
  };

  function tileLayerSetup() {
    var tileLayerSettings = mapSettings["tile_layer"];
    var tileLayerOptions = tileLayerSettings["options"];
    tileLayerOptions["maxZoom"] = tileLayerOptions["max_zoom"];
    delete tileLayerOptions["max_zoom"];

    var tileLayer = L.tileLayer(tileLayerSettings["url_template"], tileLayerOptions)
    tileLayer.addTo(_map);
  };

  function onResize() {
    var mapPos = _mapElement.offset();
    var windowHeight = $(window).height();
    var newHeight = Math.max(windowHeight - mapPos.top - 10, 100);

    if (newHeight != _currentMapHeight) {
      _mapElement.height(newHeight);
      _map.invalidateSize();
      _currentMapHeight = newHeight;
    }
  };

  function addPolylines() {
    var polylineOptions = mapSettings["polyline"]["options"];
    for (var i = 0; i < _activities.length; i++) {
      var activity = _activities[i];
      var polyline = L.polyline(activity["latlngs"], polylineOptions);
      polyline.addTo(_map);
      _polyLines.push(polyline);
    }
  };

  function initMarkers() {
    for (var i = 0; i < _activities.length; i++) {
      var activity = _activities[i];
      var latlngs = activity["latlngs"];
      var marker = L.marker(latlngs[latlngs.length - 1]);
      _markers.push(marker);

      // Ugly hack to downsize the photos and popups on small screens.
      if ($(window).width() > 600) {
        var photoColumns = 2;
        var photoFactor = 1.0;
      } else {
        var photoColumns = 2;
        var photoFactor = 0.5;
      }

      var content = _popupMaker(activity, photoColumns, photoFactor);
      var popupWidth = content.getAttribute("data-max-width");
      var popup = L.popup({minWidth: 300, maxWidth: "auto"});

      popup.setContent(content);
      marker.bindPopup(popup);
    }

    // Register handler for popup opens on the map. This handler will
    // set the src attribute on the img tags based on the data-url
    // attribute in the img tag.
    _map.on("popupopen", function(e) {
      $(e.popup.getContent()).find('img:not([src])').each(function() {
        $(this).attr("src", $(this).attr("data-url"));
      });
    });
  }

  function placeMarkers() {
    if (_markersPlaced)
      return;

    $(_markers).each(function() { this.addTo(_map); });
    _markersPlaced = true;
  }

  function removeMarkers() {
    if (!_markersPlaced)
      return

    $(_markers).each(function() { _map.removeLayer(this); });
    _markersPlaced = false;
  }

  function toggleMarkers() {
    var zoomLevel = _map.getZoom();
    if (zoomLevel >= 6) {  // XXX: magic number...
      placeMarkers();
    } else {
      removeMarkers();
    }
  }

  function init() {
    viewSetup();
    tileLayerSetup();
    addPolylines();
    initMarkers();

    // Register some handlers for updating the map
    $(window).resize(onResize);

    _map.on('zoomend', toggleMarkers);

    // This is just to remove the fullscreen container when clicked
    // on, but maybe that should go somewhere else altogether...
    $("#fullscreen-container").click(function () {
      $(this).fadeOut(function() {
        $("#fullscreen-img").attr("src", "");
        $("#whole-page-container").fadeIn();
      });
    });
  }

  // Fix the minimum zoom level to whatever fitBounds() sets for the
  // corners...
  function fitBoundsSetMinZoom() {

    function _fitBoundsCompleted() {
        _map.off("zoomend", _fitBoundsCompleted);
        var fittedZoomLevel = _map.getZoom();
        _map.setMinZoom(fittedZoomLevel);
    };
    _map.on('zoomend', _fitBoundsCompleted)
    fitBounds();
  }

  return {
    "init": init,
    "fitBoundsSetMinZoom": fitBoundsSetMinZoom,
  };


};


/*
 * Create a popup element for every marker based on the activity.
 */
function simplePopupForActivity(a) {
  var photoColumns = 2;
  var photoFactor = 0.5;
  var popupRoot = document.createElement("div");
  $(popupRoot).addClass("activity-popup");
  var popupTitle = document.createElement("h5");
  $(popupTitle).text(a["name"])
  $(popupRoot).append(popupTitle);

  var popupDesc = document.createElement("div");
  $(popupDesc).text(a["date"])
  $(popupRoot).append(popupDesc);

  // Ugh, table...
  var imgTable = document.createElement("table");
  $(imgTable).addClass("photos-table");

  var imgTbody= document.createElement("tbody");
  $(imgTable).append(imgTbody);

  var imgTr = null;
  var i = 0;
  a["photos"].forEach(function(p) {
    if (i % photoColumns == 0) {
      imgTr = document.createElement("tr");
      $(imgTbody).append(imgTr);
    }
    var imgTd = document.createElement("td");
    $(imgTd).addClass("photo-table-cell");
    $(imgTr).append(imgTd)
    var img = document.createElement("img");
    $(imgTd).append(img);
    img.setAttribute("data-url", p["url"]);
    img.setAttribute("data-large-url", p["large"]["url"]);
    img.setAttribute("data-large-width", p["large"]["width"]);
    img.setAttribute("data-large-height", p["large"]["height"]);

    img.setAttribute("width", parseInt(p["width"] * photoFactor));
    img.setAttribute("height", parseInt(p["height"] * photoFactor));
    $(img).addClass("img-rounded")

    // Allow fullscreen by using the fullscreen-img tag
    // provided in the base.html template...
    $(img).click(function() {
      var url = $(this).attr("data-large-url");
      var fullImg = $("#fullscreen-img")
      fullImg.attr("src", url);
      $("#whole-page-container").fadeOut(function() {
        $("#fullscreen-container").fadeIn();
      });
    });
    i++;
  });
  $(popupRoot).append(imgTable);
  return popupRoot;
}
