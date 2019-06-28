window.INCLUDE_URI = "/static/novnc/";

var cmd_host = undefined;
var vnc_host = undefined;

var connected = false;
var ping_id = undefined;
var ping_interval = undefined;

var page_change = false;

var pingsock = undefined;
var fail_count = 0;
var curr_hosts = undefined;

var end_time = undefined;
var cid = undefined;
var waiting_for_container = false;

$(function() {
   
    function format_date(date) {
        return date.toISOString().slice(0, -5).replace("T", " ");
    }

    function fetchData() {
        window.fetch("/api/stats/" + window.reqid)
        .then(function(res) {
          return res.json();
        }).then(function(data) {
          handle_data_update(data);
          setTimeout(fetchData, 5000);
        }).catch(function() {
          setTimeout(fetchData, 5000);
        });
    }

    function handle_data_update(data) {
        if (data.page_url && data.page_url_secs) {
            var date = new Date(data.page_url_secs * 1000);
            var date_time = format_date(date).split(" ");
            //$("#currLabel").html("Loaded <b>" + data.page_url + "</b> from <b>" + url_date + "</b>");
            $(".rel_message").hide();
            $("#curr-date").html(date_time[0]);
            $("#curr-time").html(date_time[1]);
            $("#curr-date-info").removeClass("loading");
            //url = data.page_url;
            if (page_change) {
                ping_interval = 10000;
                page_change = false;
            }
            if (sparkline) {
                sparkline.move_current(date);
            }
        }
        
        var any_data = false;

        if (data.hosts && data.hosts.length > 0) {
            if (data.hosts != curr_hosts) {
                //$("#statsHosts").empty();
                $("#statsHosts li").hide();
                $.each(data.hosts, function(i, host) {
                    //var elem = document.createElement("li");
                    //$(elem).text(host);
                    //$("#statsHosts").append(elem);
                    $("#statsHosts li[data-id='" + host + "']").show();
                });
                
                data.hosts = curr_hosts;
                $("#statsHostsWrap").show();
            }
            any_data = true;
        }

        if (data.urls) {
            $("#statsCount").text(data.urls);
            $("#statsCountWrap").show();
            any_data = true;
        }
            
        if (data.min_sec && data.max_sec) {
            var min_date = new Date(data.min_sec * 1000);
            var max_date = new Date(data.max_sec * 1000);
            $(".rel_message").hide();
            $("#statsFrom").html(format_date(min_date).replace(" ", "<br>"));
            $("#statsTo").html(format_date(max_date).replace(" ", "<br>"));
            $("#statsSpanWrap").show();
            any_data = true;
        }
        
        if (any_data) {
            $(".session-info").show();
            $("#session-loading").hide();
        }
        
        if (data.ttl != undefined) {
            set_time_left(data.ttl);
        }
        
        update_replay_state();
    }

    function update_replay_state() {
        var full_url = "/browse/" + coll + "/" + curr_ts + "/" + url;

        window.history.replaceState({}, "", full_url);
    }
    
    function set_time_left(time_left) {
        end_time = Math.floor(new Date().getTime() / 1000 + time_left);
    }

    // Browser navigate
    $("#browser-selector td:not(:empty)").click(function(e) {
        var path = $(this).attr("data-path");
        var full_url = window.location.origin + "/browse/" + path + "/" + curr_ts + "/" + url;
        window.location.href = full_url;
    });
    

    // Update request dt
    window.on_change_curr_ts = function(ts) {      
        if (pingsock) {
            pingsock.send(JSON.stringify({"ts": ts}));
            $(".rel_message").show();
        }
    }

    function update_countdown() {
        if (!end_time) {
            return;
        }
        var curr = Math.floor(new Date().getTime() / 1000);
        var secdiff = end_time - curr;

        if (secdiff < 0) {
            window.location.href = window.location.origin + "/";
            return;
        }

        var min = Math.floor(secdiff / 60);
        var sec = secdiff % 60;
        if (sec <= 9) {
            sec = "0" + sec;
        }
        if (min <= 9) {
            min = "0" + min;
        }

        $("#expire").text(min + ":" + sec);       
    }
    
    // Countdown updater
    cid = setInterval(update_countdown, 1000);
    
    // INIT
    //init_container();

    if (coll) {
        var browser = $("#browser-selector td[data-path='" + coll + "']");
        browser.addClass("selected");

        var platform = $("#browser-selector thead").find("th").eq($(browser).index());

        $("#browser-text").text($(browser).attr("data-name") + " on " + platform.text());
        $("#browser-icon").attr("src", browser.find("img").attr("src"));
        $("#browser-icon").removeClass("hidden");
        $("#browser-label").text(browser.find("label").text());

        //$("#about-link").text("about " + browserTH.text());
        $("#about-link").attr("href", browser.attr("data-about-url"));
        $(".about-browser").show();
    }

    $(window).on("message", function(e) {
        var data = e.originalEvent.data;
        window.reqid = data.reqid;
        fetchData();
    });

});




