$(document).ready(function () {
    var $comments_div = $("*[data-hotdoc-role=comments]").first();
    var repo = $comments_div.attr('data-github-repo');
    var issue_id = $comments_div.attr('data-github-issue-id');
    var url = "https://github.com/" + repo + "/issues/" + issue_id;
    var api_url = "https://api.github.com/repos/" + repo + "/issues/" + issue_id + "/comments";

    $.ajax(api_url, {
        headers: {Accept: "application/vnd.github.v3.html+json"},
        dataType: "json",
        success: function(comments) {
            $comments_div.append("Visit the <b><a href='" + url + "'>Github Issue</a></b> to comment on this post");
            $.each(comments, function(i, comment) {
                var date = new Date(comment.created_at);

                var t = "<div class='gh-comment'>";
                t += "<img src='" + comment.user.avatar_url + "' width='24px'>";
                t += "<b><a href='" + comment.user.html_url + "'>" + comment.user.login + "</a></b>";
                t += " posted on ";
                t += "<em>" + date.toUTCString() + "</em>";
                t += "<hr>";
                t += comment.body_html;
                t += "</div>";
                $comments_div.append(t);
            });
        },
        error: function() {
            $comments_div.append("Comments are not open for this post yet.");
        }
    });
});
