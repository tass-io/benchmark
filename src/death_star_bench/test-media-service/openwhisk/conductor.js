function main(params) {
    let depth = params.depth
    let path = params.path
    let here = path[depth]
    switch (here) {
        case "nginx": return { action: 'bench-06-media-nginx', params }
        case "id": return { action: 'bench-06-media-id', params }
        case "movie-id": return { action: 'bench-06-media-movie-id', params }
        case "text-service": return { action: 'bench-06-media-text-service', params }
        case "user-service": return { action: 'bench-06-media-user-service', params }
        case "rating": return { action: 'bench-06-media-rating', params }
        case "compose-review": return { action: 'bench-06-media-compose-review', params }
        case "movie-review": return { action: 'bench-06-media-movie-review', params }
        case "user-review": return { action: 'bench-06-media-user-review', params }
        case "review-storage": return { action: 'bench-06-media-review-storage', params }
        default: return { params }
    }
}
