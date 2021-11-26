function main(params) {
    let depth = params.depth
    let path = params.path
    let here = path[depth]
    switch (here) {
        case "nginx": return { action: 'bench-07-social-nginx', params }
        case "search": return { action: 'bench-07-social-search', params }
        case "make-post": return { action: 'bench-07-social-make-post', params }
        case "read-timeline": return { action: 'bench-07-social-read-timeline', params }
        case "follow": return { action: 'bench-07-social-follow', params }
        case "text": return { action: 'bench-07-social-text', params }
        case "media": return { action: 'bench-07-social-media', params }
        case "user-tag": return { action: 'bench-07-social-user-tag', params }
        case "url-shortener": return { action: 'bench-07-social-url-shortener', params }
        case "compose-post": return { action: 'bench-07-social-compose-post', params }
        case "post-storage": return { action: 'bench-07-social-post-storage', params }
        default: return { params }
    }
}

